#!/usr/bin/env python3
"""
Production Validator — FTES (First-Try Execution Score)

Executes generated code on actual Databricks workspace.
Separates "syntactically correct" (FTS) from "actually works" (FTES).

Usage:
    validator = ProductionValidator(workspace_host, warehouse_id)
    ftes_score = validator.execute_and_score(code, code_type="sql")
"""

import json
import time
import subprocess
import re
from pathlib import Path
from typing import Optional, Tuple

class ProductionValidator:
    """Execute and validate generated code on Databricks."""
    
    def __init__(self, workspace_host: str, warehouse_id: str, profile: str = "default"):
        """
        Initialize validator with workspace connection.
        
        Args:
            workspace_host: e.g., "dbc-61514402-8451.cloud.databricks.com"
            warehouse_id: e.g., "4bbaafe9538467a0"
            profile: Databricks CLI profile
        """
        self.workspace_host = workspace_host
        self.warehouse_id = warehouse_id
        self.profile = profile
        self.catalog = "finserv"
        self.schema = "eval_sandbox"  # isolated schema for testing
        
    def setup_test_schema(self) -> bool:
        """Ensure eval sandbox schema exists."""
        sql = f"CREATE SCHEMA IF NOT EXISTS {self.catalog}.{self.schema}"
        _, error = self._run_sql(sql)
        return error is None
    
    def execute_and_score(self, code: str, code_type: str = "sql", 
                         timeout_sec: int = 60) -> Tuple[float, dict]:
        """
        Execute generated code and score based on success/failure.
        
        Args:
            code: Generated SQL or Python code
            code_type: "sql" or "python"
            timeout_sec: Max execution time
            
        Returns:
            (ftes_score: 0-2.0, details: dict with error info)
        """
        details = {
            "code_type": code_type,
            "executed": False,
            "error": None,
            "execution_time_sec": 0,
            "output_rows": 0,
        }
        
        try:
            start = time.time()
            
            if code_type == "sql":
                ftes = self._execute_sql_code(code, details)
            elif code_type == "python":
                ftes = self._execute_python_code(code, details)
            else:
                details["error"] = f"Unknown code_type: {code_type}"
                return 0.0, details
            
            details["execution_time_sec"] = round(time.time() - start, 2)
            return ftes, details
            
        except Exception as e:
            details["error"] = str(e)
            return 0.0, details
    
    def _execute_sql_code(self, code: str, details: dict) -> float:
        """Execute SQL code via Databricks SQL API."""
        # Inject catalog.schema context if needed
        contextualized_code = self._inject_context(code, "sql")
        
        # Execute via Statements API
        result, error = self._run_sql(contextualized_code, timeout_sec=30)
        
        if error:
            details["error"] = error
            return 0.0  # Complete failure
        
        details["executed"] = True
        details["output_rows"] = result.get("row_count", 0) if result else 0
        
        # Scoring: 2.0 = executed successfully, 1.0 = executed with warnings
        # 0.0 = failed
        return 2.0 if result else 1.0
    
    def _execute_python_code(self, code: str, details: dict) -> float:
        """Execute Python code as a temporary notebook job."""
        # Create temp notebook
        notebook_name = f"/tmp/eval_test_{int(time.time())}"
        
        try:
            # Write notebook to workspace
            self._write_notebook(notebook_name, code)
            
            # Submit job with serverless compute
            run_id = self._submit_notebook_job(notebook_name)
            
            # Poll for completion
            success = self._poll_job_completion(run_id, timeout_sec=60)
            
            if success:
                details["executed"] = True
                return 2.0
            else:
                details["error"] = f"Job {run_id} failed or timed out"
                return 0.0
                
        finally:
            # Cleanup
            self._delete_notebook(notebook_name)
    
    def _run_sql(self, sql: str, timeout_sec: int = 30) -> Tuple[Optional[dict], Optional[str]]:
        """
        Execute SQL via Databricks Statements API.
        Returns (result_dict, error_message)
        """
        import urllib.request, urllib.error
        import os
        
        api_key = os.environ.get("DATABRICKS_TOKEN") or self._get_token_from_profile()
        if not api_key:
            return None, "No Databricks auth token found"
        
        host = f"https://{self.workspace_host}"
        url = f"{host}/api/2.0/sql/statements"
        
        payload = json.dumps({
            "warehouse_id": self.warehouse_id,
            "statement": sql,
            "wait_timeout": f"{min(timeout_sec, 50)}s"
        }).encode()
        
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=timeout_sec + 10) as resp:
                result = json.load(resp)
                
                # Check for errors in response
                if result.get("status") == "FAILED":
                    return None, result.get("error_message", "Unknown error")
                
                return result, None
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            return None, f"HTTP {e.code}: {error_body[:200]}"
        except Exception as e:
            return None, str(e)
    
    def _inject_context(self, code: str, language: str) -> str:
        """Inject catalog/schema context into code if missing."""
        if language == "sql":
            # If code doesn't reference catalog.schema, inject it
            if not re.search(r"\b\w+\.\w+\.", code):
                # Assume unqualified table names should use eval schema
                code = f"-- Context: {self.catalog}.{self.schema}\n" + code
        return code
    
    def _get_token_from_profile(self) -> Optional[str]:
        """Get auth token from Databricks CLI config."""
        try:
            result = subprocess.run(
                ["databricks", "auth", "token", "-p", self.profile],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None
    
    def _write_notebook(self, path: str, code: str) -> None:
        """Write Python code as notebook to workspace."""
        subprocess.run(
            ["databricks", "workspace", "import",
             "--file", "/dev/stdin", "--language", "PYTHON", path],
            input=code.encode(),
            check=True,
            timeout=10
        )
    
    def _delete_notebook(self, path: str) -> None:
        """Delete temporary notebook."""
        try:
            subprocess.run(
                ["databricks", "workspace", "delete", path],
                check=False,
                timeout=5
            )
        except:
            pass  # Best effort
    
    def _submit_notebook_job(self, notebook_path: str) -> str:
        """Submit notebook as job with serverless compute. Returns run_id."""
        job_spec = {
            "tasks": [{
                "task_key": "test",
                "notebook_task": {
                    "notebook_path": notebook_path,
                    "source": "WORKSPACE"
                },
                "queue": {"enabled": True}  # Serverless
            }]
        }
        
        result = subprocess.run(
            ["databricks", "jobs", "submit", "--json"],
            input=json.dumps(job_spec).encode(),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("run_id", "0")
        else:
            raise RuntimeError(f"Failed to submit job: {result.stderr}")
    
    def _poll_job_completion(self, run_id: str, timeout_sec: int = 60) -> bool:
        """Poll job until completion or timeout. Returns True if successful."""
        start = time.time()
        while time.time() - start < timeout_sec:
            result = subprocess.run(
                ["databricks", "runs", "get", "--run-id", run_id],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                state = data.get("state", "")
                
                if state == "TERMINATED":
                    # Check result state
                    result_state = data.get("state_message", "")
                    return "SUCCESS" in result_state
                elif state in ["INTERNAL_ERROR", "SKIPPED"]:
                    return False
            
            time.sleep(2)
        
        return False  # Timeout


def demo_ftes_scoring():
    """Example of FTES validation."""
    validator = ProductionValidator(
        workspace_host="dbc-61514402-8451.cloud.databricks.com",
        warehouse_id="4bbaafe9538467a0"
    )
    
    # Test SQL code
    sql_code = """
    SELECT 
      CURRENT_TIMESTAMP() as test_time,
      CAST(3.14 AS DECIMAL(10,2)) as test_decimal
    LIMIT 1
    """
    
    ftes, details = validator.execute_and_score(sql_code, code_type="sql")
    print(f"FTES: {ftes}/2.0")
    print(f"Details: {details}")


if __name__ == "__main__":
    demo_ftes_scoring()
