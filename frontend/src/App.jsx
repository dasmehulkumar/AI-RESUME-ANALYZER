import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle, AlertCircle, Lightbulb, ChevronLeft } from 'lucide-react';

function App() {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const analyzeResume = async () => {
    if (!file || !jobDescription) {
      setError("Please upload a resume and provide a job description.");
      return;
    }
    
    setError(null);
    setLoading(true);

    const formData = new FormData();
    formData.append('resume', file);
    formData.append('job_description', jobDescription);

    try {
      const response = await fetch('http://localhost:5000/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to analyze resume. Make sure the backend is running.");
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setJobDescription('');
    setResults(null);
    setError(null);
  };

  return (
    <div className="app-container">
      <div className="header">
        <h1>AI Resume Analyzer</h1>
        <p>Optimize your resume against any job description with advanced AI.</p>
      </div>

      {!results && !loading && (
        <div className="glass-panel upload-section">
          <div 
            className="drop-zone" 
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current.click()}
          >
            <UploadCloud />
            <h3>{file ? file.name : "Drag & Drop Resume"}</h3>
            <p style={{marginTop: '0.5rem', color: 'var(--text-muted)'}}>
              {file ? "Click to change file" : "or click to browse (PDF only)"}
            </p>
            <input 
              type="file" 
              accept=".pdf" 
              hidden 
              ref={fileInputRef} 
              onChange={handleFileChange} 
            />
          </div>

          <div className="form-group">
            <label>Job Description</label>
            <textarea 
              placeholder="Paste the target job description here..."
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
            ></textarea>
          </div>

          {error && <div style={{gridColumn: 'span 2', color: 'var(--danger-color)', textAlign: 'center'}}>{error}</div>}

          <button 
            className="btn-primary" 
            onClick={analyzeResume}
            disabled={!file || !jobDescription}
          >
            Analyze Match
          </button>
        </div>
      )}

      {loading && (
        <div className="glass-panel loader-container">
          <div className="spinner"></div>
          <h2>Analyzing your resume...</h2>
          <p style={{color: 'var(--text-muted)', marginTop: '0.5rem'}}>Our AI is comparing your skills with the job requirements.</p>
        </div>
      )}

      {results && !loading && (
        <div className="glass-panel results-section">
          <button onClick={resetForm} style={{background: 'none', border: 'none', color: 'var(--primary-color)', cursor: 'pointer', display: 'flex', alignItems: 'center', marginBottom: '2rem', fontSize: '1rem', fontWeight: '600'}}>
            <ChevronLeft size={20} /> Back to Upload
          </button>

          <div className="scores-container">
            <div className="score-card">
              <div className="circular-progress" style={{'--progress': `${results.match_score}%`}}>
                <span className="progress-value">{results.match_score}%</span>
              </div>
              <div className="score-label">Overall Match Score</div>
            </div>
            
            <div className="score-card">
              <div className="circular-progress" style={{'--progress': `${results.ats_score}%`, '--primary-color': 'var(--secondary-color)'}}>
                <span className="progress-value">{results.ats_score}%</span>
              </div>
              <div className="score-label">ATS Readiness</div>
            </div>
          </div>

          <div className="skills-container">
            <div className="skill-box">
              <h3 style={{color: 'var(--success-color)'}}><CheckCircle size={20}/> Matched Skills ({results.matched_skills.length})</h3>
              <div className="badges">
                {results.matched_skills.length > 0 ? (
                  results.matched_skills.map((skill, i) => (
                    <span key={i} className="badge matched" style={{animationDelay: `${i * 0.05}s`}}>{skill}</span>
                  ))
                ) : (
                  <p style={{color: 'var(--text-muted)'}}>No specific skills matched.</p>
                )}
              </div>
            </div>

            <div className="skill-box">
              <h3 style={{color: 'var(--danger-color)'}}><AlertCircle size={20}/> Missing Skills ({results.missing_skills.length})</h3>
              <div className="badges">
                {results.missing_skills.length > 0 ? (
                  results.missing_skills.map((skill, i) => (
                    <span key={i} className="badge missing" style={{animationDelay: `${i * 0.05}s`}}>{skill}</span>
                  ))
                ) : (
                  <p style={{color: 'var(--text-muted)'}}>Great! No missing skills identified.</p>
                )}
              </div>
            </div>
          </div>

          {results.suggestions.length > 0 && (
            <div className="suggestions-box">
              <h3><Lightbulb size={20} color="var(--warning-color)"/> Actionable Suggestions</h3>
              <ul>
                {results.suggestions.map((suggestion, i) => (
                  <li key={i}>{suggestion}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
