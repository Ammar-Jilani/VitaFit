// frontend/src/components/AIChat.jsx
import React, { useState, useEffect } from 'react';
import './AIChat.css';

const AIChat = ({ BACKEND_BASE_URL, sessionId }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [aiOverview, setAiOverview] = useState('');
    const [overviewLoading, setOverviewLoading] = useState(true);
    const [overviewError, setOverviewError] = useState('');

    const getErrorMessage = (errorData) => {
        if (errorData && errorData.detail) {
            if (typeof errorData.detail === 'string') {
                return errorData.detail;
            }
            if (Array.isArray(errorData.detail)) {
                return errorData.detail.map(err => {
                    const loc = err.loc ? err.loc.join('.') : 'unknown';
                    return `${loc} - ${err.msg}`;
                }).join('; ');
            }
        }
        return 'An unknown error occurred.';
    };

    useEffect(() => {
        const fetchAiOverview = async () => {
            if (!sessionId) {
                setOverviewLoading(false);
                return;
            }

            setOverviewLoading(true);
            setOverviewError('');

            try {
                const response = await fetch(`${BACKEND_BASE_URL}/ai/overview`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    // *** IMPORTANT CHANGE HERE FOR OVERVIEW ***
                    body: JSON.stringify({
                        session_id: sessionId,
                        message: "Please provide an initial health overview based on my fitness data." // A default message for overview
                    }),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    const errorMessage = getErrorMessage(errorData);
                    throw new Error(errorMessage);
                }

                const data = await response.json();
                // Backend returns 'response' for both chat and overview based on your main.py
                setAiOverview(data.response);
                setMessages([{ sender: 'ai', text: data.response }]);
            } catch (error) {
                console.error('Error fetching AI health overview:', error.message);
                setOverviewError(`Error getting health overview: ${error.message}`);
                setMessages([{ sender: 'ai', text: `Failed to load initial overview: ${error.message}` }]);
            } finally {
                setOverviewLoading(false);
            }
        };

        fetchAiOverview();
    }, [sessionId, BACKEND_BASE_URL]);

    const sendMessage = async () => {
        if (input.trim() === '' || loading) return;

        const userMessage = { sender: 'user', text: input };
        setMessages((prevMessages) => [...prevMessages, userMessage]);
        setInput('');

        setLoading(true);

        try {
            const response = await fetch(`${BACKEND_BASE_URL}/ai/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                // *** IMPORTANT CHANGE HERE FOR CHAT ***
                body: JSON.stringify({
                    session_id: sessionId,
                    message: userMessage.text // Send the user's input as 'message'
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                const errorMessage = getErrorMessage(errorData);
                throw new Error(errorMessage);
            }

            const data = await response.json();
            // Backend returns 'response' for both chat and overview
            const aiResponse = { sender: 'ai', text: data.response };
            setMessages((prevMessages) => [...prevMessages, aiResponse]);

        } catch (error) {
            console.error('Error sending message to AI chat:', error);
            setMessages((prevMessages) => [...prevMessages, { sender: 'ai', text: `Error: ${error.message}` }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="ai-chat-container">
            <h3>AI Fitness Assistant</h3>
            <div className="chat-messages">
                {overviewLoading && <div className="message ai">Loading your health overview...</div>}
                {overviewError && <div className="message ai error-message">{overviewError}</div>}
                {!overviewLoading && messages.length === 0 && !overviewError && (
                    <div className="message ai">Hi there! Ask me anything about fitness or nutrition based on your plan.</div>
                )}
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.sender}`}>
                        {msg.text}
                    </div>
                ))}
                {loading && <div className="message ai">Thinking...</div>}
            </div>
            <div className="chat-input">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => { if (e.key === 'Enter') sendMessage(); }}
                    placeholder="Ask me anything..."
                    disabled={loading || overviewLoading || !sessionId}
                />
                <button onClick={sendMessage} disabled={loading || overviewLoading || !sessionId}>Send</button>
            </div>
        </div>
    );
};

export default AIChat;