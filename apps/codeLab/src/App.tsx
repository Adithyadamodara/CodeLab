import { useState, useEffect } from 'react';
import { Lab } from './components/Lab';
import { Play, User } from 'lucide-react';

function App() {
  const [isLabLaunched, setIsLabLaunched] = useState(false);
  const [userId, setUserId] = useState<string>('');

  useEffect(() => {
    const savedUserId = localStorage.getItem('guest_id');
    if (savedUserId) {
      setUserId(savedUserId);
    }
  }, []);

  const handleLaunch = async () => {
    let currentUserId = userId;
    if (!currentUserId) {
      currentUserId = `guest-${crypto.randomUUID().slice(0, 8)}`;
      localStorage.setItem('guest_id', currentUserId);
      setUserId(currentUserId);
    }
    
    // Call the launch endpoint to provision or retrieve pod
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      await fetch(`${API_URL}/launch/${currentUserId}`, { method: 'POST' });
    } catch (err) {
      console.error("Failed to trigger pod launch", err);
    }

    setIsLabLaunched(true);
  };

  const handleExit = () => {
    localStorage.removeItem('guest_id');
    setUserId('');
    setIsLabLaunched(false);
  };

  if (isLabLaunched && userId) {
    return <Lab userId={userId} onExit={handleExit} />;
  }

  return (
    <div className="app-container">
      <main className="landing-page">
        <h1 className="landing-title">CodeLab</h1>
        <p className="landing-subtitle">
          Welcome to CodeLab! {userId ? `You are logged in as ${userId}. ` : 'Login as a guest and '} Click the button below to start coding!
        </p>
        <button
          className="launch-btn"
          onClick={handleLaunch}
        >
          {userId ? <Play size={20} fill="currentColor" /> : <User size={20} />}
          {userId ? 'Resume Python Lab' : 'Login as Guest & Launch'}
        </button>
      </main>
    </div>
  );
}

export default App;
