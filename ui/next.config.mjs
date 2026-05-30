/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // single WS connection; avoid double-mount in dev
};
export default nextConfig;
