import { useState } from 'react'

// Controlled input: React state holds the text, so we can clear it or show an
// error without touching the DOM ourselves.
export default function AddStreamForm({ onAdd, disabled }) {
  const [text, setText] = useState('')
  const [error, setError] = useState(null)

  function handleSubmit(event) {
    event.preventDefault() // stop the browser from reloading the page
    const problem = onAdd(text)
    setError(problem)
    if (!problem) setText('')
  }

  return (
    <form className="add-form" onSubmit={handleSubmit}>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Twitch URL or channel name"
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !text.trim()}>Add</button>
      {error && <span className="add-form__error">{error}</span>}
    </form>
  )
}
