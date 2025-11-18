/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  // Only set NEXT_PUBLIC_API_URL if explicitly provided
  // In Docker Space, we want it undefined so frontend uses relative URLs (proxied by Next.js)
  ...(process.env.NEXT_PUBLIC_API_URL && {
    env: {
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    },
  }),
  async rewrites() {
    // In Docker Space, proxy /api/* requests to backend on port 8000
    // This allows frontend (7860) to communicate with backend (8000) internally
    const API_HOST = process.env.BACKEND_HOST || 'http://localhost:8000';
    console.log(`[Next.js] Setting up API proxy: /api/* -> ${API_HOST}/api/*`);
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

