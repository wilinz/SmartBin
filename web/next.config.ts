import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  env: {
    // 自定义环境变量
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:5001',
    NEXT_PUBLIC_APP_NAME: 'SmartBin 智能垃圾分拣系统',
    NEXT_PUBLIC_APP_VERSION: '1.0.0'
  }
};

export default nextConfig;
