// One Twitch player. The iframe is a separate page from twitch.tv, so we can't
// see clicks inside it; that's why focus/remove live on our own bar above it.
export default function StreamTile({ channel, isFocused, muted, onFocus, onRemove }) {
  // Twitch refuses to play unless `parent` matches the hostname of the page
  // embedding it. Reading it at runtime makes the same code work on
  // localhost and on a deployed domain.
  const parent = window.location.hostname
  const src = `https://player.twitch.tv/?channel=${channel}&parent=${parent}&muted=${muted}`

  return (
    <div className={isFocused ? 'tile tile--focus' : 'tile'}>
      <div className="tile__bar">
        <button className="tile__name" onClick={onFocus} title="Focus this stream">
          {isFocused ? '★ ' : ''}{channel}
        </button>
        <button className="tile__remove" onClick={onRemove} aria-label={`Remove ${channel}`}>
          ×
        </button>
      </div>
      {/* allow="autoplay" lets the player start inside our page; browsers
          still only autoplay when muted unless the user has interacted. */}
      <iframe src={src} title={`${channel} on Twitch`} allow="autoplay; fullscreen" allowFullScreen />
    </div>
  )
}
