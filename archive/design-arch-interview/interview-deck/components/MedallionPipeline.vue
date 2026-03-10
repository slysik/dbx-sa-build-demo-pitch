<script setup>
const props = defineProps({
  title: { type: String, default: 'FinServ ETL Pipeline - Medallion Architecture' },
  subtitle: { type: String, default: 'Databricks Lakehouse | Unity Catalog | Serverless' },
  sources: {
    type: Array,
    default: () => ['Card Networks', 'POS Terminals', 'Mobile Wallets']
  },
  bronze: {
    type: Object,
    default: () => ({
      label: 'BRONZE',
      desc: 'Raw Streaming Ingestion',
      stats: '45,244 transactions',
      bullets: [
        'ACID / exactly-once',
        'Partitioned by date',
        'Immutable audit trail',
        'Time travel enabled'
      ]
    })
  },
  silver: {
    type: Object,
    default: () => ({
      label: 'SILVER',
      desc: 'Cleanse / Validate / Mask',
      stats: '45,244 transactions',
      bullets: [
        'PII masked (PCI-DSS)',
        'DQ validation + quarantine',
        'Risk score enrichment',
        'MERGE INTO (upserts)'
      ]
    })
  },
  gold: {
    type: Object,
    default: () => ({
      label: 'GOLD',
      desc: 'Aggregates + ML Features',
      stats: '',
      bullets: [
        'cardholder_features (10)',
        'merchant_risk (500)',
        'hourly_volume (20)',
        '22+ ML features/user',
        'Z-ORDER optimized'
      ]
    })
  },
  ml: {
    type: Object,
    default: () => ({
      label: 'MLflow',
      desc: 'Fraud Detection Model',
      stats: '',
      bullets: [
        'GradientBoosting',
        'RandomForest',
        'Experiment tracking',
        'Model comparison',
        'Batch inference > Delta'
      ]
    })
  },
  governance: {
    type: String,
    default: 'Unity Catalog — Governance | Lineage | RBAC | Column Masks | Audit'
  },
  serving: {
    type: Array,
    default: () => ['Power BI / Genie AI', 'DBSQL Dashboards', 'Fraud Predictions']
  },
  serverlessFixes: {
    type: Array,
    default: () => [
      'availableNow trigger',
      'UC Volume checkpoints',
      'tableExists() not isDelta',
      'Class balance fix',
      'MLflow registry fallback',
      'Missing F import'
    ]
  }
})
</script>

<template>
  <div class="pipeline-wrap">
    <!-- Title -->
    <div class="text-center mb-2">
      <div class="text-lg font-bold text-gray-800">{{ title }}</div>
      <div class="text-xs text-gray-500">{{ subtitle }}</div>
    </div>

    <!-- Main flow -->
    <div class="flex items-start gap-1">
      <!-- Sources -->
      <div class="flex flex-col gap-1 mt-8">
        <div
          v-for="src in sources"
          :key="src"
          class="source-box"
        >
          {{ src }} <span class="text-gray-400 ml-1">&rArr;</span>
        </div>
      </div>

      <!-- Bronze -->
      <div class="layer-box bronze">
        <div class="layer-label bronze-label">{{ bronze.label }}</div>
        <div class="layer-desc">{{ bronze.desc }}</div>
        <div v-if="bronze.stats" class="layer-stats">{{ bronze.stats }}</div>
        <ul class="layer-bullets">
          <li v-for="b in bronze.bullets" :key="b">{{ b }}</li>
        </ul>
      </div>

      <div class="arrow">&rArr;</div>

      <!-- Silver -->
      <div class="layer-box silver">
        <div class="layer-label silver-label">{{ silver.label }}</div>
        <div class="layer-desc">{{ silver.desc }}</div>
        <div v-if="silver.stats" class="layer-stats">{{ silver.stats }}</div>
        <ul class="layer-bullets">
          <li v-for="b in silver.bullets" :key="b">{{ b }}</li>
        </ul>
      </div>

      <div class="arrow">&rArr;</div>

      <!-- Gold -->
      <div class="layer-box gold">
        <div class="layer-label gold-label">{{ gold.label }}</div>
        <div class="layer-desc">{{ gold.desc }}</div>
        <div v-if="gold.stats" class="layer-stats">{{ gold.stats }}</div>
        <ul class="layer-bullets">
          <li v-for="b in gold.bullets" :key="b">{{ b }}</li>
        </ul>
      </div>

      <div class="arrow">&rArr;</div>

      <!-- ML -->
      <div class="layer-box mlflow">
        <div class="layer-label mlflow-label">{{ ml.label }}</div>
        <div class="layer-desc">{{ ml.desc }}</div>
        <div v-if="ml.stats" class="layer-stats">{{ ml.stats }}</div>
        <ul class="layer-bullets">
          <li v-for="b in ml.bullets" :key="b">{{ b }}</li>
        </ul>
      </div>
    </div>

    <!-- Governance bar -->
    <div class="gov-bar">{{ governance }}</div>

    <!-- Bottom row -->
    <div class="flex gap-2 mt-1">
      <!-- Serverless fixes -->
      <div class="fixes-box">
        <div class="font-bold text-xs mb-1 text-red-700">Serverless Fixes</div>
        <ol class="text-[9px] list-decimal list-inside text-red-600 leading-tight">
          <li v-for="fix in serverlessFixes" :key="fix">{{ fix }}</li>
        </ol>
      </div>

      <!-- Serving layer -->
      <div class="flex-1">
        <div class="text-xs text-center text-gray-500 italic mb-1">Serving Layer</div>
        <div class="flex gap-2 justify-center">
          <div
            v-for="svc in serving"
            :key="svc"
            class="serving-box"
          >
            {{ svc }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pipeline-wrap {
  font-family: 'Segoe UI', system-ui, sans-serif;
  padding: 4px 8px;
  transform: scale(0.95);
  transform-origin: top center;
}

.source-box {
  background: #f1f3f5;
  border: 1.5px solid #adb5bd;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 10px;
  font-weight: 600;
  color: #495057;
  white-space: nowrap;
}

.layer-box {
  border-radius: 12px;
  padding: 6px 10px;
  min-width: 150px;
  flex: 1;
}

.bronze { background: #f4e4c1; border: 2px solid #c4a35a; }
.silver { background: #e8edf2; border: 2px solid #8899aa; }
.gold { background: #fef3c7; border: 2px solid #d4a017; }
.mlflow { background: #dbeafe; border: 2px solid #6b9bd2; }

.layer-label {
  font-size: 16px;
  font-weight: 800;
  text-align: center;
  letter-spacing: 2px;
}
.bronze-label { color: #8B4513; }
.silver-label { color: #2C3E50; }
.gold-label { color: #B8860B; }
.mlflow-label { color: #1A3A4A; }

.layer-desc {
  font-size: 9px;
  text-align: center;
  color: #555;
  margin-bottom: 2px;
}

.layer-stats {
  font-size: 9px;
  text-align: center;
  font-weight: 600;
  color: #333;
  margin-bottom: 2px;
}

.layer-bullets {
  font-size: 8px;
  color: #444;
  padding-left: 10px;
  margin: 0;
  line-height: 1.4;
}

.arrow {
  display: flex;
  align-items: center;
  font-size: 18px;
  color: #888;
  padding-top: 30px;
}

.gov-bar {
  background: #1a5c3a;
  color: white;
  text-align: center;
  padding: 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  margin-top: 6px;
  letter-spacing: 0.5px;
}

.fixes-box {
  background: #fff5f5;
  border: 1.5px solid #e03131;
  border-radius: 6px;
  padding: 4px 8px;
  min-width: 140px;
}

.serving-box {
  background: #f3e8ff;
  border: 1.5px solid #9775ba;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 10px;
  font-weight: 600;
  color: #5a3d7a;
  text-align: center;
}
</style>
