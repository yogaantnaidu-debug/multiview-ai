import { useEffect, useState } from 'react'
import { MAX_STREAMS, parseChannel, readChannelsFromUrl, writeChannelsToUrl } from './channels'
import AddStreamForm from './AddStreamForm'
import StreamTile from './StreamTile'
import AiPanel from './AiPanel'
import useBackend from './useBackend'
import './App.css'

// Equal-grid columns: 1 stream fills the width, up to 4 make a 2x2, 5–6 use 3 columns.
function equalColumns(count) {
  if (count <= 1) return 1
  return count <= 4 ? 2 : 3
}

export default function App() {
  // Lazy initialiser: read the URL once on first render, not on every render.
  const [channels, setChannels] = useState(readChannelsFromUrl)
  const [focusedChoice, setFocusedChoice] = useState(null)
  // false = everything muted; true = only the focused stream has sound.
  const [audioOn, setAudioOn] = useState(false)
  // 'focus' = one big tile + small ones; 'grid' = all tiles the same size.
  const [layout, setLayout] = useState('focus')
  const [directorNote, setDirectorNote] = useState(null)

  // Focus is derived, not stored separately: if the focused stream is removed,
  // we fall back to the first one instead of pointing at a stream that's gone.
  const focused = channels.includes(focusedChoice) ? focusedChoice : channels[0] ?? null

  const { connected, stats, sendManualFocus } = useBackend(channels, focused, (channel, reason) => {
    setFocusedChoice(channel)
    setDirectorNote(`Director moved ${channel} to focus: ${reason}.`)
  })

  // Keep the URL in sync whenever the list changes.
  useEffect(() => writeChannelsToUrl(channels), [channels])

  // Returns an error message for the form, or null on success.
  function addChannel(input) {
    const name = parseChannel(input)
    if (!name) return 'Not a valid channel: 4–25 letters, digits or _.'
    if (channels.includes(name)) return `${name} is already on the grid.`
    if (channels.length >= MAX_STREAMS) return `Max ${MAX_STREAMS} streams.`
    setChannels([...channels, name])
    return null
  }

  function removeChannel(name) {
    setChannels(channels.filter((c) => c !== name))
  }

  // A click is a human decision, so the backend locks the Director for 60 s.
  function focusByHand(name) {
    setFocusedChoice(name)
    sendManualFocus(name)
    setDirectorNote(null)
  }

  let gridClass = 'grid'
  if (layout === 'grid') gridClass = 'grid grid--equal'
  else if (channels.length === 1) gridClass = 'grid grid--single'

  return (
    <div className="app">
      <header className="header">
        <h1>MultiView AI</h1>
        <AddStreamForm onAdd={addChannel} disabled={channels.length >= MAX_STREAMS} />
        <button onClick={() => setAudioOn(!audioOn)} disabled={!channels.length}>
          {audioOn ? 'Mute all' : 'Unmute focused'}
        </button>
        <button onClick={() => setLayout(layout === 'focus' ? 'grid' : 'focus')} disabled={!channels.length}>
          {layout === 'focus' ? 'Grid layout' : 'Focus layout'}
        </button>
        <span className="header__count">{channels.length}/{MAX_STREAMS}</span>
      </header>

      {channels.length === 0 ? (
        <p className="empty">Add a Twitch channel to start, e.g. <code>shroud</code>.</p>
      ) : (
        <div className="layout">
          {/* Tiles stay in the same DOM order and CSS moves the focused one
              into the big slot. Re-ordering the DOM would make React remount
              the iframes, and every stream would reload on each focus change. */}
          <main className={gridClass} style={{ '--cols': equalColumns(channels.length) }}>
            {channels.map((name) => (
              <StreamTile
                key={name}
                channel={name}
                isFocused={name === focused}
                muted={!(audioOn && name === focused)}
                onFocus={() => focusByHand(name)}
                onRemove={() => removeChannel(name)}
              />
            ))}
          </main>
          <AiPanel
            channels={channels}
            stats={stats}
            connected={connected}
            focused={focused}
            note={directorNote}
          />
        </div>
      )}
    </div>
  )
}
