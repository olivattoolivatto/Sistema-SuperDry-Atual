/**
 * URL do backend — detecta automaticamente o host correto.
 * - localhost/127.0.0.1 → usa a variável de ambiente (.env)
 * - outro host (Tailscale, rede local, celular, etc.) → mesmo host, porta 8001
 * Importar como: import { BACKEND_URL } from '../lib/backendUrl';
 */
const _env = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const _host = window.location.hostname;
const _port = window.location.port;

// localhost/127.0.0.1 → usa .env (desenvolvimento)
// porta explícita 8001 → acesso direto na rede local
// sem porta (80/443) → servido pelo tunnel/proxy, usa mesma origem sem porta
export const BACKEND_URL = (_host === 'localhost' || _host === '127.0.0.1')
  ? _env
  : _port === '8001'
    ? `${window.location.protocol}//${_host}:8001`
    : `${window.location.protocol}//${_host}`;

export default BACKEND_URL;
