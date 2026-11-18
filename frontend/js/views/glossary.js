/**
 * Trading EZ - Glosario de Conceptos Cuantitativos y Financieros
 */

export function openGlossaryModal() {
  const modal = document.getElementById("glossary-modal");
  if (!modal) return;
  modal.classList.add("open");
}

export function closeGlossaryModal() {
  const modal = document.getElementById("glossary-modal");
  if (!modal) return;
  modal.classList.remove("open");
}
