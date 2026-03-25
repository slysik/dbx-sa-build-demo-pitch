/**
 * OE Detail Lookup JavaScript
 * 
 * Integrates Domino forms with Databricks order/invoice lookup.
 * Calls the OEDetailLookup Java agent via Ajax, parses the response,
 * and populates form fields.
 * 
 * Dependencies: jQuery (loaded in Domino form header)
 * 
 * Usage:
 *   1. Include this file in your Domino form
 *   2. Bind to invoice field: $("#InvoiceNo").on("change", function() { lookupInvoice($(this).val()); })
 *   3. Or bind to a button: $("#LookupBtn").on("click", function() { lookupInvoice($("#InvoiceNo").val()); })
 */

(function($) {
  'use strict';

  /**
   * Formats a date string from YYYY-MM-DD to MM/DD/YYYY
   * Handles null, undefined, empty, and "null" string values
   * 
   * @param {string} dateStr - Date in YYYY-MM-DD format from Databricks
   * @returns {string} Formatted date MM/DD/YYYY or empty string if invalid
   */
  function formatDate(dateStr) {
    // Handle null, undefined, empty, or literal "null" string
    if (!dateStr || dateStr === null || dateStr === undefined || dateStr === "null" || dateStr.trim() === "") {
      return "";
    }

    // Split on hyphen: YYYY-MM-DD
    var parts = dateStr.split("-");
    if (parts.length !== 3) {
      // Invalid format, return as-is
      return dateStr;
    }

    // Rearrange to MM/DD/YYYY
    var month = parts[1];
    var day = parts[2];
    var year = parts[0];

    return month + "/" + day + "/" + year;
  }

  /**
   * Looks up order/invoice details from Databricks
   * 
   * Calls the OEDetailLookup Java agent, parses the ~*~ delimited response,
   * and populates form fields. Handles errors, timeouts, and data formatting.
   * 
   * Response format on success:
   *   "custno~*~custname~*~orderdate~*~shipdate"
   * 
   * Response format on error:
   *   "ERROR~*~<error message>"
   *   "NOTFOUND~*~<not found message>"
   * 
   * @param {string} invoiceNo - Invoice number to look up
   */
  function lookupInvoice(invoiceNo) {
    // ========== INPUT VALIDATION ==========
    if (!invoiceNo) {
      alert("Please enter an invoice number.");
      return;
    }

    invoiceNo = invoiceNo.trim();
    if (invoiceNo === "") {
      alert("Please enter an invoice number.");
      return;
    }

    // ========== SHOW LOADING STATE ==========
    var $lookupBtn = $("#LookupBtn");
    var $invoiceField = $("#InvoiceNo");
    
    $lookupBtn.prop("disabled", true).text("Loading...");
    $invoiceField.prop("disabled", true);

    // Clear previous results
    clearFormFields();

    // ========== AJAX CALL TO JAVA AGENT ==========
    $.ajax({
      url: "/" + getFormDatabasePath() + "/OEDetailLookup?OpenAgent",
      method: "POST",
      contentType: "application/x-www-form-urlencoded",
      data: "invoice=" + encodeURIComponent(invoiceNo),
      dataType: "text",
      timeout: 30000,  // 30 second timeout

      // ========== SUCCESS: PARSE RESPONSE ==========
      success: function(response) {
        // Trim whitespace from response
        response = response.trim();

        // Split on delimiter
        var parts = response.split("~*~");

        // Check for error response
        if (parts.length >= 2 && (parts[0] === "ERROR" || parts[0] === "NOTFOUND")) {
          var errorMsg = parts[1] || "Unknown error occurred.";
          showError(errorMsg);
          return;
        }

        // Validate we got the expected 4 fields
        if (parts.length < 4) {
          showError("Unexpected response format from server.");
          return;
        }

        // ========== POPULATE FORM FIELDS ==========
        // Field mapping (current):
        // 0 = custno (Customer Number)
        // 1 = custname (Customer Name)
        // 2 = orderdate (Order Date)
        // 3 = shipdate (Ship Date)

        // Helper to handle null/"null" string values
        function getValue(value) {
          if (!value || value === "null" || value.trim() === "") {
            return "";
          }
          return value;
        }

        var custNo = getValue(parts[0]);
        var custName = getValue(parts[1]);
        var orderDate = formatDate(getValue(parts[2]));
        var shipDate = formatDate(getValue(parts[3]));

        // Set form field values
        $("#CustomerNo").val(custNo);
        $("#CustomerName").val(custName);
        $("#OrderDate").val(orderDate);
        $("#ShipDate").val(shipDate);

        // Optionally set a success message or highlight
        showSuccess("Invoice details loaded successfully.");
      },

      // ========== AJAX ERROR: NETWORK FAILURE ==========
      error: function(xhr, status, error) {
        if (status === "timeout") {
          showError("Request timed out. Please try again.");
        } else {
          showError("Unable to connect to server. Please check your connection and try again.");
        }
        clearFormFields();
      },

      // ========== CLEANUP: RESTORE UI STATE ==========
      complete: function() {
        $lookupBtn.prop("disabled", false).text("Lookup");
        $invoiceField.prop("disabled", false);
      }
    });
  }

  /**
   * Clears all order detail form fields
   */
  function clearFormFields() {
    $("#CustomerNo").val("");
    $("#CustomerName").val("");
    $("#OrderDate").val("");
    $("#ShipDate").val("");
  }

  /**
   * Displays an error message to the user
   * 
   * @param {string} message - Error message text
   */
  function showError(message) {
    var $errorDiv = $("#ErrorMessage");
    if ($errorDiv.length === 0) {
      // Create error div if it doesn't exist
      $errorDiv = $("<div id='ErrorMessage'></div>");
      $("#InvoiceNo").after($errorDiv);
    }
    $errorDiv.html("<span style='color: red; font-weight: bold;'>Error: " + escapeHtml(message) + "</span>");
  }

  /**
   * Displays a success message to the user (optional)
   * 
   * @param {string} message - Success message text
   */
  function showSuccess(message) {
    var $successDiv = $("#SuccessMessage");
    if ($successDiv.length === 0) {
      // Create success div if it doesn't exist
      $successDiv = $("<div id='SuccessMessage'></div>");
      $("#ShipDate").after($successDiv);
    }
    $successDiv.html("<span style='color: green;'>" + escapeHtml(message) + "</span>");

    // Auto-hide success message after 5 seconds
    setTimeout(function() {
      $successDiv.fadeOut(300);
    }, 5000);
  }

  /**
   * Escapes HTML special characters to prevent injection
   * 
   * @param {string} text - Text to escape
   * @returns {string} Escaped text
   */
  function escapeHtml(text) {
    var map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
  }

  /**
   * Returns the database path for the current Domino form
   * Extracts from the form's parent database URL
   * 
   * @returns {string} Database path (e.g., "mydb.nsf")
   */
  function getFormDatabasePath() {
    // Get the database path from the current Domino form
    // This is typically available via a hidden field or Domino context variable
    // Common approach: look for a hidden field set by Domino
    var dbPath = $("#DatabasePath").val();
    
    if (!dbPath) {
      // Fallback: extract from current document.location
      // Example: https://domino.example.com/keep/open/mydb.nsf
      var pathParts = window.location.pathname.split("/");
      dbPath = pathParts[pathParts.length - 1];
    }

    return dbPath || "database.nsf";
  }

  /**
   * ========== FORM FIELD BINDINGS ==========
   * 
   * Call lookupInvoice() when:
   *   1. Invoice number field changes (onChange)
   *   2. Lookup button is clicked
   * 
   * To add a new field from the Java agent response:
   * ========================================
   * 
   * 1. Add the field to the SQL query in OEDetailLookup.java
   *    Example: SELECT custno, custname, orderdate, shipdate, ponumber FROM ...
   * 
   * 2. Append it to the delimited string in the Java agent (after the last ~*~)
   *    Example: custno + "~*~" + custname + "~*~" + orderdate + "~*~" + shipdate + "~*~" + ponumber
   * 
   * 3. Add the field mapping here:
   *    a. Update the validation: if (parts.length < 5) instead of < 4
   *    b. Add the field extraction:
   *       var poNumber = getValue(parts[4]);  // 4 = 0-based position of ponumber
   *    c. Add the field assignment:
   *       $("#PONumber").val(poNumber);
   * 
   * 4. Update this comment with the new field count and mapping
   * 
   * Current field mapping (4 fields):
   *   0 = custno (Customer Number)
   *   1 = custname (Customer Name)
   *   2 = orderdate (Order Date) [formatted MM/DD/YYYY]
   *   3 = shipdate (Ship Date) [formatted MM/DD/YYYY, nullable]
   * 
   */

  // Wait for document ready
  $(document).ready(function() {
    // Bind to invoice number field onChange
    $("#InvoiceNo").on("change", function() {
      lookupInvoice($(this).val());
    });

    // Bind to lookup button click
    $("#LookupBtn").on("click", function(e) {
      e.preventDefault();
      lookupInvoice($("#InvoiceNo").val());
    });
  });

  // Export function to global scope for manual calling if needed
  window.lookupInvoice = lookupInvoice;

})(jQuery);
