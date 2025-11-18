/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  async rewrites() {
    // In Docker Space, proxy /api/* requests to backend on port 8000
    // This allows frontend (7860) to communicate with backend (8000) internally
    const API_HOST = process.env.BACKEND_HOST || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${API_HOST}/api/:path*`,
      },
      {
        source: '/ws/:path*',
        destination: `${API_HOST}/ws/:path*`,
      },
    ];
  },
}

module.exports = nextConfig

