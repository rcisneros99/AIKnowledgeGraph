import React, { useState } from 'react';

const ChatBot = ({ onContextChange }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const sendMessage = async () => {
    if (!input.trim()) return;

    const newMessages = [...messages, { text: input, sender: 'user' }];
    setMessages(newMessages);
    setInput('');

    try {
      const response = await fetch('http://localhost:8000/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: input
        }),
      });

      const data = await response.json();
      setMessages([...newMessages, { text: data.response, sender: 'bot' }]);

      if (data.recommended_products && data.recommended_products.length > 0) {
        console.log("Setting recommended products:", data.recommended_products);
        onContextChange(`recommended:${data.recommended_products.join(',')}`);
      } else {
        console.log("No recommended products received");
        onContextChange('');
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages([...newMessages, { 
        text: 'Sorry, I encountered an error. Please try again.', 
        sender: 'bot' 
      }]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-[600px] border rounded-lg shadow-lg bg-white">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.sender === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[70%] rounded-lg p-3 ${
                message.sender === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white border border-gray-200 shadow-sm text-gray-800'
              }`}
            >
              {message.sender === 'bot' ? (
                <div className="prose prose-sm">
                  {message.text?.split('\n').map((line, i) => (
                    <p key={i} className="mb-2">
                      {line}
                    </p>
                  ))}
                </div>
              ) : (
                message.text
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="border-t p-4">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1 border rounded-lg p-2"
            placeholder="Ask about products..."
          />
          <button
            onClick={sendMessage}
            className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatBot;
