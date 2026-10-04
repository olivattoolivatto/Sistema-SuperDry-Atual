import React, { useState, useEffect, useRef } from 'react';

// ── DecimalField ──────────────────────────────────────────────────────────────
// Substituto pro <input type="number"> em TODO o sistema. NÃO use type="number"
// em campo novo nenhum -- motivo (pedido explícito do Diego, 04/10/2026):
//   1. Exige foco em 2 cliques pra selecionar o valor (o primeiro clique vai pro
//      spinner/stepper, não seleciona o texto) -- ruim pra sobrescrever rápido.
//   2. Em pt-BR o usuário digita vírgula ("2,5") e o campo zera/rejeita; digitar
//      ponto ("2.5") também falha em boa parte dos navegadores/locale.
// Esse componente é texto puro (inputMode="decimal", sem spinner), aceita tanto
// vírgula quanto ponto, nunca reseta o que a pessoa digitou no meio da edição,
// e o clique único já seleciona tudo (onFocus). Ver pendência de migração dos
// demais <input type="number"> ainda existentes no sistema (grep "type=\"number\""
// em frontend/src).
export function parseDecimalInput(raw) {
  if (raw == null) return null;
  const cleaned = String(raw).trim().replace(',', '.');
  if (cleaned === '' || cleaned === '.' || cleaned === '-') return null;
  const n = parseFloat(cleaned);
  return Number.isFinite(n) ? n : null;
}

export function DecimalField({
  value, onChange, placeholder, className, selectAllOnFocus = true, inputRef, onBlur, ...rest
}) {
  const [text, setText] = useState(value != null ? String(value) : '');
  const focusedRef = useRef(false);

  // Sincroniza com valor externo só quando o campo NÃO está sendo digitado
  // agora -- evita "puxar o tapete" do que a pessoa está digitando.
  useEffect(() => {
    if (!focusedRef.current) setText(value != null ? String(value) : '');
  }, [value]);

  return (
    <input
      {...rest}
      ref={inputRef}
      type="text"
      inputMode="decimal"
      placeholder={placeholder}
      className={className}
      value={text}
      onFocus={e => { focusedRef.current = true; if (selectAllOnFocus) e.target.select(); }}
      onBlur={e => { focusedRef.current = false; onBlur && onBlur(e); }}
      onChange={e => {
        // só deixa dígito, vírgula, ponto e sinal de menos -- qualquer outra
        // tecla (letra etc.) é ignorada, mas nunca reseta o que já foi digitado.
        const v = e.target.value.replace(/[^0-9.,-]/g, '');
        setText(v);
        onChange(parseDecimalInput(v));
      }}
    />
  );
}

export default DecimalField;
