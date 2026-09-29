import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ApiError, createDesign, listDesigns, pngSrc } from '@/api/client';
import type { DesignSummary } from '@/api/types';

const errorText = (e: unknown) => (e instanceof ApiError ? String(e.detail) : e instanceof Error ? e.message : String(e));

export function Library() {
  const [designs, setDesigns] = useState<DesignSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    listDesigns()
      .then((d) => alive && setDesigns(d))
      .catch((e) => alive && setError(errorText(e)));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="library">
      <header className="library-header">
        <h1>XStitchLab</h1>
        <p className="muted">Design library</p>
      </header>
      <NewDesignForm />
      {error && <p className="error">Could not load designs: {error}</p>}
      {!error && designs === null && <p className="muted">Loading…</p>}
      {designs && designs.length === 0 && <p className="muted">No designs yet.</p>}
      {designs && (
        <ul className="card-grid">
          {designs.map((d) => (
            <li key={d.slug}>
              <DesignCard design={d} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function DesignCard({ design: d }: { design: DesignSummary }) {
  return (
    <Link to={`/d/${d.slug}`} className="card">
      <div className="card-thumb">
        {d.thumbnail_png ? <img src={pngSrc(d.thumbnail_png)} alt="" /> : <span className="muted">no pattern</span>}
      </div>
      <div className="card-body">
        <h2>{d.title}</h2>
        <p className="mono muted">{d.slug}</p>
        {d.has_pattern && (
          <p className="muted">
            {d.width}×{d.height} · {d.colors} colours · {d.stitches} stitches
          </p>
        )}
        <p className="badges">
          {!d.has_input && <span className="badge">no input</span>}
          {!d.has_pattern && <span className="badge">no pattern</span>}
        </p>
      </div>
    </Link>
  );
}

function NewDesignForm() {
  const navigate = useNavigate();
  const [slug, setSlug] = useState('');
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const d = await createDesign(slug.trim(), title.trim());
      navigate(`/d/${d.slug}`);
    } catch (err) {
      setError(errorText(err));
      setBusy(false);
    }
  };

  return (
    <form className="new-design" onSubmit={submit}>
      <strong>New design</strong>
      <input
        placeholder="slug, e.g. 27-holstentor-lubeck"
        value={slug}
        onChange={(e) => setSlug(e.target.value)}
        required
        pattern="[a-z0-9][a-z0-9-]*"
        title="lowercase letters, digits and hyphens"
      />
      <input placeholder="title" value={title} onChange={(e) => setTitle(e.target.value)} required />
      <button type="submit" disabled={busy || !slug.trim() || !title.trim()}>
        {busy ? 'Creating…' : 'Create'}
      </button>
      {error && <span className="error">{error}</span>}
    </form>
  );
}
