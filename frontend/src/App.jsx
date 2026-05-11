import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userQuery = input;
    setMessages(prev => [...prev, { text: userQuery, sender: 'user' }]);
    setInput('');
    setLoading(true);

    try {
      // 1. Submit task to FastAPI
      const response = await fetch('http://127.0.0.1:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userQuery }),
      });
      const { task_id } = await response.json();

      // 2. Poll for the result
      let isDone = false;
      while (!isDone) {
        const statusRes = await fetch(`http://127.0.0.1:8000/status/${task_id}`);
        const data = await statusRes.json();

        if (data.status === 'SUCCESS') {
          setMessages(prev => [...prev, { text: data.response, sender: 'bot' }]);
          setLoading(false);
          isDone = true;
        } else {
          // Wait 2 seconds before polling again
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      }
    } catch (error) {
      console.error("Connection error:", error);
      setMessages(prev => [...prev, { text: "Connection error. Is FastAPI running?", sender: 'bot' }]);
      setLoading(false);
    }
  };

  return (
    <div className="chat-app">
      <header><h1>Cardia AI</h1></header>
      
      <div className="message-container">
        {messages.map((msg, i) => (
          <div key={i} className={`message-bubble ${msg.sender}`}>
            {msg.text}
          </div>
        ))}
        {loading && <div className="message-bubble bot typing">Cardia is researching...</div>}
        <div ref={scrollRef} />
      </div>

      <form onSubmit={sendMessage} className="input-area">
        <input 
          value={input} 
          onChange={(e) => setInput(e.target.value)} 
          placeholder="Ask about heart health..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>Send</button>
      </form>
    </div>
  );
}

export default App;