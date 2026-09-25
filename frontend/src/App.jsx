import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options)
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const payload = await response.json()
      message = payload.detail || message
    } catch {
      // Keep the HTTP fallback when the response is not JSON.
    }
    throw new Error(message)
  }
  return response.json()
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '—'
  const total = Math.max(0, Math.floor(Number(seconds)))
  const minutes = Math.floor(total / 60)
  return `${minutes}:${String(total % 60).padStart(2, '0')}`
}

function App() {
  const [apiOnline, setApiOnline] = useState(null)
  const [videos, setVideos] = useState([])
  const [videoError, setVideoError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState('')
  const [searchMode, setSearchMode] = useState('text')
  const [query, setQuery] = useState('')
  const [queryImage, setQueryImage] = useState(null)
  const [topK, setTopK] = useState(8)
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [results, setResults] = useState([])
  const [selectedMoment, setSelectedMoment] = useState(null)
  const playerRef = useRef(null)

  const loadVideos = useCallback(async () => {
    try {
      const data = await apiRequest('/videos')
      setVideos(data)
      setVideoError('')
      setApiOnline(true)
    } catch (error) {
      setVideoError(error.message)
      setApiOnline(false)
    }
  }, [])

  useEffect(() => {
    async function initialize() {
      try {
        await apiRequest('/health')
        setApiOnline(true)
        await loadVideos()
      } catch {
        setApiOnline(false)
      }
    }
    initialize()
  }, [loadVideos])

  useEffect(() => {
    const hasActiveJob = videos.some((video) =>
      ['pending', 'processing'].includes(video.status),
    )
    if (!hasActiveJob) return undefined
    const timer = window.setInterval(loadVideos, 2000)
    return () => window.clearInterval(timer)
  }, [videos, loadVideos])

  useEffect(() => {
    if (!selectedMoment || !playerRef.current) return
    const player = playerRef.current
    const seek = () => {
      player.currentTime = Number(selectedMoment.timestamp_seconds || 0)
      player.play().catch(() => {})
    }
    player.addEventListener('loadedmetadata', seek, { once: true })
    player.load()
    return () => player.removeEventListener('loadedmetadata', seek)
  }, [selectedMoment])

  async function handleUpload(event) {
    event.preventDefault()
    const form = event.currentTarget
    const file = form.elements.video.files[0]
    if (!file) return

    const payload = new FormData()
    payload.append('file', file)
    if (form.elements.title.value.trim()) payload.append('title', form.elements.title.value.trim())

    setUploading(true)
    setUploadMessage('')
    try {
      const video = await apiRequest('/videos', { method: 'POST', body: payload })
      setUploadMessage(`“${video.title}” was accepted and is being indexed.`)
      form.reset()
      await loadVideos()
    } catch (error) {
      setUploadMessage(error.message)
    } finally {
      setUploading(false)
    }
  }

  async function handleSearch(event) {
    event.preventDefault()
    const payload = new FormData()
    if (searchMode === 'text') {
      if (!query.trim()) {
        setSearchError('Enter a description to search for.')
        return
      }
      payload.append('query', query.trim())
    } else {
      if (!queryImage) {
        setSearchError('Choose an image to search with.')
        return
      }
      payload.append('file', queryImage)
    }
    payload.append('top_k', String(topK))

    setSearching(true)
    setSearchError('')
    setResults([])
    try {
      const path = searchMode === 'text' ? '/search/text' : '/search/image'
      setResults(await apiRequest(path, { method: 'POST', body: payload }))
    } catch (error) {
      setSearchError(error.message)
    } finally {
      setSearching(false)
    }
  }

  const counts = videos.reduce(
    (summary, video) => ({ ...summary, [video.status]: (summary[video.status] || 0) + 1 }),
    {},
  )

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="VideoSearch home">
          <span className="brand-mark">VS</span><span>VideoSearch</span>
        </a>
        <div className={`api-status ${apiOnline ? 'online' : apiOnline === false ? 'offline' : ''}`}>
          <span className="status-dot" />
          {apiOnline === null ? 'Checking API' : apiOnline ? 'Local API online' : 'API offline'}
        </div>
      </header>

      <main id="top">
        <section className="hero-section">
          <div className="eyebrow">Semantic video retrieval</div>
          <h1>Search inside video,<br />not just around it.</h1>
          <p>Upload a clip, let CLIP and pgvector index its visual moments, then find the right timestamp with natural language or an example image.</p>
          <div className="pipeline" aria-label="Processing pipeline">
            <span>Video</span><b>→</b><span>ffmpeg</span><b>→</b><span>CLIP</span><b>→</b><span>pgvector</span>
          </div>
        </section>

        <section className="metrics" aria-label="Library summary">
          <div><strong>{videos.length}</strong><span>Total videos</span></div>
          <div><strong>{counts.ready || 0}</strong><span>Ready to search</span></div>
          <div><strong>{(counts.pending || 0) + (counts.processing || 0)}</strong><span>Indexing</span></div>
          <div><strong>{counts.failed || 0}</strong><span>Failed tests</span></div>
        </section>

        <section className="workspace-grid">
          <article className="panel upload-panel">
            <div className="panel-heading"><span className="step-number">01</span><div><h2>Add a video</h2><p>Index a short clip for semantic search.</p></div></div>
            <form onSubmit={handleUpload}>
              <label>Display title <span>optional</span><input name="title" type="text" maxLength="200" placeholder="Night traffic downtown" /></label>
              <label className="file-drop">
                <span className="file-icon">＋</span><strong>Choose a video file</strong>
                <input name="video" type="file" accept="video/mp4,video/quicktime,video/webm,video/x-msvideo" required />
                <small>MP4, MOV, AVI, or WebM</small>
              </label>
              <button className="primary-button" type="submit" disabled={uploading || apiOnline === false}>{uploading ? 'Uploading…' : 'Upload and index'}</button>
              {uploadMessage && <p className="form-message">{uploadMessage}</p>}
            </form>
          </article>

          <article className="panel search-panel">
            <div className="panel-heading"><span className="step-number">02</span><div><h2>Search every moment</h2><p>Describe a scene or provide a visual example.</p></div></div>
            <div className="mode-tabs" role="tablist" aria-label="Search type">
              <button className={searchMode === 'text' ? 'active' : ''} onClick={() => setSearchMode('text')} type="button">Text</button>
              <button className={searchMode === 'image' ? 'active' : ''} onClick={() => setSearchMode('image')} type="button">Image</button>
            </div>
            <form onSubmit={handleSearch}>
              {searchMode === 'text' ? (
                <label>What are you looking for?<textarea value={query} onChange={(event) => setQuery(event.target.value)} maxLength="200" placeholder="A person riding a bicycle through the city" rows="3" /></label>
              ) : (
                <label>Example image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => setQueryImage(event.target.files[0] || null)} /></label>
              )}
              <div className="search-controls">
                <label>Results<select value={topK} onChange={(event) => setTopK(Number(event.target.value))}>{[5, 8, 10, 15, 20].map((count) => <option key={count}>{count}</option>)}</select></label>
                <button className="primary-button" type="submit" disabled={searching || apiOnline === false}>{searching ? 'Searching…' : 'Run semantic search'}</button>
              </div>
              {searchError && <p className="error-message">{searchError}</p>}
            </form>
          </article>
        </section>

        <section className="section-block" id="results">
          <div className="section-heading"><div><span className="section-kicker">Ranked retrieval</span><h2>Search results</h2></div><span className="result-count">{results.length ? `${results.length} moments` : 'Waiting for a query'}</span></div>
          {!results.length && !searching ? (
            <div className="empty-state"><span>⌕</span><p>Your closest matching video moments will appear here.</p></div>
          ) : (
            <div className="results-grid">
              {results.map((result, index) => (
                <button className="result-card" key={result.id} type="button" onClick={() => setSelectedMoment(result)}>
                  <div className="thumbnail-wrap"><img src={`${API_BASE}${result.thumbnail_url}`} alt={`Frame from ${result.video_title}`} /><span className="timestamp">{formatDuration(result.timestamp_seconds)}</span><span className="rank">#{index + 1}</span></div>
                  <div className="result-copy"><strong>{result.video_title}</strong><span>Similarity {Number(result.similarity).toFixed(3)} · matched {formatDuration(result.matched_timestamp_seconds)}</span></div>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="section-block library-section">
          <div className="section-heading"><div><span className="section-kicker">Indexed collection</span><h2>Video library</h2></div><button className="text-button" type="button" onClick={loadVideos}>Refresh</button></div>
          {videoError && <p className="error-message">{videoError}</p>}
          <div className="video-table">
            {videos.map((video) => (
              <div className="video-row" key={video.id}>
                <div className="video-avatar">{video.title.slice(0, 2).toUpperCase()}</div>
                <div className="video-info"><strong>{video.title}</strong><span>{video.original_filename || 'Uploaded video'}</span></div>
                <span className={`status-pill ${video.status}`}>{video.status}</span><span className="duration">{formatDuration(video.duration_seconds)}</span>
                <button className="play-button" type="button" disabled={video.status !== 'ready'} onClick={() => setSelectedMoment({ video_id: video.id, video_title: video.title, video_url: `/media/videos/${video.id}`, timestamp_seconds: 0 })}>Play</button>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer><span>VideoSearch</span><span>FastAPI · CLIP · PostgreSQL · pgvector · Docker</span></footer>

      {selectedMoment && (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setSelectedMoment(null)}>
          <div className="player-modal" role="dialog" aria-modal="true" aria-label={`Playing ${selectedMoment.video_title}`}>
            <div className="player-header"><div><span>Playing from {formatDuration(selectedMoment.timestamp_seconds)}</span><h2>{selectedMoment.video_title}</h2></div><button type="button" aria-label="Close player" onClick={() => setSelectedMoment(null)}>×</button></div>
            <video ref={playerRef} controls playsInline src={`${API_BASE}${selectedMoment.video_url}`} />
          </div>
        </div>
      )}
    </div>
  )
}

export default App
