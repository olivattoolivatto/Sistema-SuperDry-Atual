# SuperDry — Credenciais de Teste

## Admin padrão
- Email: `admin@superdry.com`
- Senha: `admin123`
- Role: `ADMIN`

(O admin é criado automaticamente no startup do backend se não existir.)

## Rotas autenticadas
Todos endpoints exceto `/api/auth/login` exigem o header:
```
Authorization: Bearer <token>
```
