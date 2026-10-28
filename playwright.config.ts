import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir:'./tests',testMatch:'**/*.spec.ts',timeout:30000,workers:1,outputDir:'artifacts/playwright',
  use:{baseURL:'http://localhost:5179',channel:'chrome',headless:true,viewport:{width:1440,height:1000},screenshot:'only-on-failure'},
  webServer:[
    {command:'python scripts/ui_server.py',url:'http://127.0.0.1:8012/api/health',timeout:30000,reuseExistingServer:false},
    {command:'npm run dev -w web -- --port 5179 --strictPort',url:'http://localhost:5179',env:{API_TARGET:'http://127.0.0.1:8012'},timeout:30000,reuseExistingServer:false},
  ],
});
