// ID genérico "TECH-001" era usado em todo o sistema pra identificar "o técnico",
// sem corresponder a nenhum usuário real cadastrado (o técnico real, Marcos, é
// USR-6249). Migração: a partir de 04/10/2026, toda CRIAÇÃO nova de
// assignment/registro usa o ID real abaixo. Leituras (consulta de tarefas do dia)
// continuam incluindo o legado "TECH-001" pra não esconder o que já estava em
// aberto sob o nome antigo -- quando não houver mais nada pendente lá, pode tirar
// o legado de TECHNICIAN_IDS_READ.
//
// Quando entrar um segundo técnico, basta: 1) cadastrar o usuário dele (role
// TECNICO), 2) ele aparecer numa futura tela de seleção de técnico (ainda não
// existe -- hoje há só 1 técnico real em uso) usando o id desse usuário no lugar
// de TECHNICIAN_ID.
export const TECHNICIAN_ID = 'USR-6249'; // Marcos

export const TECHNICIAN_IDS_READ = ['TECH-001', TECHNICIAN_ID].join(',');
