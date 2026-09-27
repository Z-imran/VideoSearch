import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const MAX_QUERY_IMAGE_DIMENSION = 1600
const QUERY_IMAGE_QUALITY = 0.85

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

async function resizeQueryImage(file) {
  const image = await createImageBitmap(file)
  const scale = Math.min(1, MAX_QUERY_IMAGE_DIMENSION / Math.max(image.width, image.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(image.width * scale))
  canvas.height = Math.max(1, Math.round(image.height * scale))
  const context = canvas.getContext('2d')
  context.fillStyle = '#ffffff'
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.drawImage(image, 0, 0, canvas.width, canvas.height)
  image.close()

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', QUERY_IMAGE_QUALITY))
  if (!blob) throw new Error('The selected image could not be prepared for search.')
  const filename = `${file.name.replace(/\.[^.]+$/, '') || 'query'}.jpg`
  return new File([blob], filename, { type: 'image/jpeg' })
}

function App() {
  const [serviceStatus, setServiceStatus] = useState('checking')
  const [uploadPolicy, setUploadPolicy] = useState({ uploads_enabled: true })
  const [videos, setVideos] = useState([])
  const [videoError, setVideoError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState('')
  const [uploadMessageType, setUploadMessageType] = useState('info')
  const [uploadJob, setUploadJob] = useState(null)
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
      return true
    } catch (error) {
      setVideoError(error.message)
      setServiceStatus('offline')
      return false
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    let failedChecks = 0
    let catalogueLoaded = false
    let timer

    async function checkService() {
      try {
        const health = await apiRequest('/health')
        if (cancelled) return
        failedChecks = 0
        setUploadPolicy(health)
        setServiceStatus('ready')
        if (!catalogueLoaded) catalogueLoaded = await loadVideos()
        if (!cancelled) timer = window.setTimeout(checkService, 15000)
      } catch {
        if (cancelled) return
        failedChecks += 1
        setServiceStatus((current) => current === 'ready' || failedChecks >= 3 ? 'offline' : 'warming')
        timer = window.setTimeout(checkService, 2000)
      }
    }

    checkService()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [loadVideos])

  useEffect(() => {
    if (!uploadJob) return undefined
    let cancelled = false

    async function checkUpload() {
      try {
        const video = await apiRequest(`/videos/${uploadJob.id}`)
        if (cancelled) return
        if (video.status === 'ready') {
          setUploadMessageType('success')
          setUploadMessage(`“${video.title}” is ready to search.`)
          setUploadJob(null)
          await loadVideos()
        } else if (video.status === 'failed') {
          setUploadMessageType('error')
          setUploadMessage(`“${video.title}” could not be processed. Try a shorter MP4, MOV, AVI, or WebM video.`)
          setUploadJob(null)
        } else {
          setUploadMessageType('info')
          setUploadMessage(`Preparing “${video.title}” for search…`)
        }
      } catch (error) {
        if (cancelled) return
        setUploadMessageType('error')
        setUploadMessage(error.message)
        setUploadJob(null)
      }
    }

    checkUpload()
    const timer = window.setInterval(checkUpload, 2000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [uploadJob, loadVideos])

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
    const maxVideoBytes = uploadPolicy.max_video_bytes || 100 * 1024 * 1024
    if (file.size > maxVideoBytes) {
      setUploadMessageType('error')
      setUploadMessage('Video exceeds the 100 MB upload limit.')
      return
    }

    const payload = new FormData()
    payload.append('file', file)
    if (form.elements.title.value.trim()) payload.append('title', form.elements.title.value.trim())

    setUploading(true)
    setUploadMessage('')
    setUploadMessageType('info')
    try {
      const video = await apiRequest('/videos', { method: 'POST', body: payload })
      setUploadJob({ id: video.id, title: video.title })
      setUploadMessage(`Preparing “${video.title}” for search…`)
      form.reset()
    } catch (error) {
      setUploadMessageType('error')
      setUploadMessage(error.message)
    } finally {
      setUploading(false)
    }
  }

  async function handleSearch(event) {
    event.preventDefault()
    if (searchMode === 'text') {
      if (!query.trim()) {
        setSearchError('Enter a description to search for.')
        return
      }
    } else {
      if (!queryImage) {
        setSearchError('Choose an image to search with.')
        return
      }
    }

    setSearching(true)
    setSearchError('')
    setResults([])
    try {
      const payload = new FormData()
      if (searchMode === 'text') {
        payload.append('query', query.trim())
      } else {
        payload.append('file', await resizeQueryImage(queryImage))
      }
      payload.append('top_k', String(topK))
      const path = searchMode === 'text' ? '/search/text' : '/search/image'
      setResults(await apiRequest(path, { method: 'POST', body: payload }))
    } catch (error) {
      setSearchError(error.message)
    } finally {
      setSearching(false)
    }
  }

  const serviceLabel = {
    checking: 'Starting search',
    warming: 'Preparing search',
    ready: 'Ready',
    offline: 'Unavailable',
  }[serviceStatus]
  const serviceReady = serviceStatus === 'ready'
  const uploadsAvailable = uploadPolicy.uploads_enabled !== false

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="VideoSearch home">
          <span className="brand-mark">VS</span><span>VideoSearch</span>
        </a>
        <div className={`api-status ${serviceStatus}`}>
          <span className="status-dot" />
          {serviceLabel}
        </div>
      </header>

      <main id="top">
        <section className="hero-section">
          <div className="eyebrow">Find moments faster</div>
          <h1>Search inside video,<br />not just around it.</h1>
          <p>Upload a short clip and find its most relevant moments using a description or an example image.</p>
        </section>

        <section className="workspace-grid">
          <article className="panel upload-panel">
            <div className="panel-heading"><span className="step-number">01</span><div><h2>Add a video</h2><p>Make a short clip searchable.</p></div></div>
            <form onSubmit={handleUpload}>
              <label>Display title <span>optional</span><input name="title" type="text" maxLength="200" placeholder="Night traffic downtown" /></label>
              <label className="file-drop">
                <span className="file-icon">＋</span><strong>Choose a video file</strong>
                <input name="video" type="file" accept="video/mp4,video/quicktime,video/webm,video/x-msvideo" required />
                <small>MP4, MOV, AVI, or WebM · Maximum 100 MB and 3 minutes</small>
              </label>
              <button className="primary-button" type="submit" disabled={uploading || Boolean(uploadJob) || !serviceReady || !uploadsAvailable}>{uploading ? 'Uploading…' : uploadJob ? 'Preparing video…' : uploadsAvailable ? 'Upload video' : 'Uploads temporarily disabled'}</button>
              {uploadMessage && <p className={`form-message ${uploadMessageType}`} aria-live="polite">{uploadMessage}</p>}
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
                <label>Example image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => setQueryImage(event.target.files[0] || null)} /><small className="field-hint">Large images are resized automatically.</small></label>
              )}
              <div className="search-controls">
                <label>Results<select value={topK} onChange={(event) => setTopK(Number(event.target.value))}>{[5, 8, 10, 15, 20].map((count) => <option key={count}>{count}</option>)}</select></label>
                <button className="primary-button" type="submit" disabled={searching || !serviceReady}>{searching ? 'Searching…' : 'Search videos'}</button>
              </div>
              {searchError && <p className="error-message">{searchError}</p>}
            </form>
          </article>
        </section>

        <section className="section-block" id="results">
          <div className="section-heading"><div><span className="section-kicker">Best matches</span><h2>Search results</h2></div><span className="result-count">{results.length ? `${results.length} moments` : 'Waiting for a query'}</span></div>
          {!results.length && !searching ? (
            <div className="empty-state"><span>⌕</span><p>Your closest matching video moments will appear here.</p></div>
          ) : (
            <div className="results-grid">
              {results.map((result, index) => (
                <button className="result-card" key={result.id} type="button" onClick={() => setSelectedMoment(result)}>
                  <div className="thumbnail-wrap"><img loading="lazy" decoding="async" src={`${API_BASE}${result.thumbnail_url}`} alt={`Frame from ${result.video_title}`} /><span className="timestamp">{formatDuration(result.timestamp_seconds)}</span><span className="rank">#{index + 1}</span></div>
                  <div className="result-copy"><strong>{result.video_title}</strong><span>Similarity {Number(result.similarity).toFixed(3)}</span></div>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="section-block library-section">
          <div className="section-heading"><div><span className="section-kicker">Available videos</span><h2>Video library</h2></div><button className="text-button" type="button" onClick={loadVideos}>Refresh</button></div>
          {videoError && <p className="error-message">{videoError}</p>}
          <div className="video-table">
            {!videos.length && <div className="library-empty">No videos are ready yet.</div>}
            {videos.map((video) => (
              <div className="video-row" key={video.id}>
                <div className="video-avatar">{video.title.slice(0, 2).toUpperCase()}</div>
                <div className="video-info"><strong>{video.title}</strong></div>
                <span className="duration">{formatDuration(video.duration_seconds)}</span>
                <button className="play-button" type="button" onClick={() => setSelectedMoment({ video_id: video.id, video_title: video.title, video_url: `/media/videos/${video.id}`, timestamp_seconds: 0 })}>Play</button>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer><span>VideoSearch</span><span>Semantic video search demo</span></footer>

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
