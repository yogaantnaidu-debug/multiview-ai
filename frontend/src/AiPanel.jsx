// Side panel: shows the numbers the Director uses, so its choices are visible,
// plus each stream's latest Chat Pulse.
export default function AiPanel({ channels, stats, connected, focused, note }) {
  const byName = Object.fromEntries((stats?.streams ?? []).map((s) => [s.channel, s]))

  let status = 'Connecting to Twitch chat…'
  if (!connected) status = 'Backend offline: the grid works, but there is no chat data.'
  else if (stats?.chat_connected) status = 'Reading Twitch chat live.'

  return (
    <aside className="panel">
      <h2>AI panel</h2>
      <p className="panel__status">{status}</p>
      {connected && <AiStatus ai={stats?.ai} />}
      {stats?.lock_remaining > 0 && (
        <p className="panel__note">You picked the focus. The Director waits another {stats.lock_remaining} s.</p>
      )}
      {note && <p className="panel__note">{note}</p>}
      {channels.map((name) => (
        <HypeRow key={name} name={name} stat={byName[name]} isFocused={name === focused} />
      ))}
    </aside>
  )
}

function AiStatus({ ai }) {
  if (!ai) return null
  if (ai.status === 'off') return <p className="panel__status">Chat Pulse: AI off (no LLM key set).</p>
  if (ai.status === 'paused') return <p className="panel__status">Chat Pulse: AI paused ({ai.reason}).</p>
  return <p className="panel__status">Chat Pulse: on, about every 30 s per busy stream.</p>
}

function HypeRow({ name, stat, isFocused }) {
  const hype = stat?.hype ?? 0
  // The bar runs from 0x to 4x, so the Director's 2.0x threshold is the middle line.
  const width = Math.min(hype / 4, 1) * 100

  let label = '–'
  if (stat) label = stat.warming_up ? 'warming up' : `${hype.toFixed(1)}x`

  return (
    <div className="hype">
      <div className="hype__top">
        <span>{isFocused ? '★ ' : ''}{name}</span>
        <span>{label}</span>
      </div>
      <div className="hype__track">
        <div className={hype > 2 ? 'hype__bar hype__bar--hot' : 'hype__bar'} style={{ width: `${width}%` }} />
        <div className="hype__threshold" />
      </div>
      {stat && (
        <div className="hype__detail">
          {stat.rate.toFixed(1)} msg/s now · normal {stat.baseline == null ? '…' : stat.baseline.toFixed(1)}
        </div>
      )}
      {stat?.pulse && (
        // {text} in JSX is always escaped: even if chat tricks the model into
        // writing HTML or a <script>, it is displayed as harmless characters.
        <div className="pulse">
          <span className={`mood mood--${stat.pulse.mood}`}>{stat.pulse.mood}</span>
          {stat.pulse.summary}
          <span className="pulse__age"> · {stat.pulse.age}s ago</span>
        </div>
      )}
    </div>
  )
}
