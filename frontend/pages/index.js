import { useState, useEffect } from 'react';
import axios from 'axios';

export default function Home() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [stage, setStage] = useState('login'); // login, loading, auth_success, result, error
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [progress, setProgress] = useState(0);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStage('loading');
    setErrorMsg('');
    setProgress(0);

    // Simulate progress
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 95) return prev;
        // Slow down as we get closer to 95
        // 0-30: Fast (Connection)
        // 30-80: Medium (Login & Navigation)
        // 80-95: Slow (Waiting for response)
        const increment = prev < 30 ? 2 : prev < 80 ? 0.5 : 0.1;
        return Math.min(prev + increment, 95);
      });
    }, 100);

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
      // Use relative path /api/grades which is proxied to backend by Next.js
      const response = await axios.post('/api/grades', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      clearInterval(interval);
      setProgress(100);

      if (response.data.status === 'success') {
        setResult(response.data);
        setStage('auth_success');
        
        // Show "Auth Success" for 2 seconds, then show result
        setTimeout(() => {
          setStage('result');
        }, 2000);
      } else {
        setErrorMsg(response.data.message || 'Unknown error occurred');
        setStage('error');
      }
    } catch (err) {
      clearInterval(interval);
      console.error(err);
      setErrorMsg(err.response?.data?.message || 'Connection failed');
      setStage('error');
    }
  };

  const handleRetry = () => {
    setStage('login');
    setUsername('');
    setPassword('');
    setErrorMsg('');
  };

  return (
    <div className="container">
      {stage === 'login' && (
        <form onSubmit={handleSubmit}>
          <h1>総機GPAジェネレータ</h1>
          <input
            type="text"
            placeholder="Waseda メール"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit">Login</button>
        </form>
      )}

      {stage === 'loading' && (
        <div className="loading">
          <h1>処理中...</h1>
          <p>ログインしてます</p>
          <div className="progress-text">{Math.round(progress)}%</div>
          <div className="progress-container">
            <div className="progress-bar" style={{ width: `${progress}%` }}></div>
          </div>
        </div>
      )}

      {stage === 'auth_success' && (
        <div className="success">
          <h1 style={{color: 'green'}}>ログインできました！</h1>
          <p>成績を集計してます...</p>
        </div>
      )}

      {stage === 'result' && result && (
        <div className="result-container">
          <div className="label">必修科目平均点</div>
          <div className="result">{result.average_score}</div>
          
          <p>Student ID: {result.student_id}</p>
          <button onClick={handleRetry}>もう見ました、満足！
        </button>
        </div>
      )}

      {stage === 'error' && (
        <div className="error-container">
          <h1 style={{color: 'red'}}>ログインに失敗しました</h1>
          <p className="error">Waseda ID または、パスワードが違います</p>
          <button onClick={handleRetry}>やり直す</button>
        </div>
      )}
    </div>
  );
}
