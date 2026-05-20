<script setup lang="ts">
import { ref } from 'vue'
import { needsToken, setToken } from '../lib/auth'

const value = ref('')

function submit() {
  const trimmed = value.value.trim()
  if (!trimmed) return
  setToken(trimmed)
  value.value = ''
  // Reload the route so any in-flight failed requests retry with the new token.
  // Simplest reliable approach — full client-side retry orchestration is
  // overkill for a single-user local tool.
  window.location.reload()
}
</script>

<template>
  <div v-if="needsToken" class="token-prompt-backdrop" role="dialog" aria-modal="true">
    <div class="token-prompt-card">
      <h2>Authentication required</h2>
      <p>
        This Mettle instance requires a token. Paste the value of your
        <code>METTLE_TOKEN</code> environment variable.
      </p>
      <form @submit.prevent="submit">
        <input
          v-model="value"
          type="password"
          autocomplete="off"
          placeholder="Paste token..."
          required
          aria-label="Mettle token"
        />
        <button type="submit">Save and reload</button>
      </form>
      <p class="token-help">
        Generate a fresh token with
        <code>python -c "import secrets; print(secrets.token_urlsafe(32))"</code>.
      </p>
    </div>
  </div>
</template>

<style scoped>
.token-prompt-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}
.token-prompt-card {
  background: var(--card-bg, #1e1e22);
  color: var(--card-fg, #e6e6e6);
  border-radius: 8px;
  padding: 1.5rem 2rem;
  max-width: 28rem;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}
.token-prompt-card h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.2rem;
}
.token-prompt-card p {
  margin: 0.25rem 0 1rem 0;
  font-size: 0.9rem;
  opacity: 0.85;
}
.token-prompt-card input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-family: monospace;
  border-radius: 4px;
  border: 1px solid #555;
  background: #2a2a2e;
  color: inherit;
  font-size: 0.9rem;
  box-sizing: border-box;
}
.token-prompt-card button {
  margin-top: 0.75rem;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: 0;
  background: #4a8df0;
  color: white;
  cursor: pointer;
  font-size: 0.9rem;
}
.token-prompt-card button:hover {
  background: #3a7dd9;
}
.token-help {
  margin-top: 1rem;
  font-size: 0.8rem;
  opacity: 0.7;
}
.token-help code {
  background: #2a2a2e;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}
</style>
