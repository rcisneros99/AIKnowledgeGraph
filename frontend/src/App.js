import React, { useState } from 'react';
import ProductGrid from './components/ProductGrid';
import ChatBot from './components/ChatBot';
import GraphVisualization from './components/GraphVisualization';

function App() {
  const [context, setContext] = useState('');
  const [recommendedIds, setRecommendedIds] = useState([]);

  const handleContextChange = (newContext) => {
    setContext(newContext);
    if (newContext && newContext.startsWith('recommended:')) {
      setRecommendedIds(newContext.split(':')[1].split(','));
    } else {
      setRecommendedIds([]);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-8">Browse our store!</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <h2 className="text-2xl font-bold mb-4">Recommended Products: </h2>
          <ProductGrid context={context} />
        </div>
        <div>
          <h2 className="text-2xl font-bold mb-4">Chat with our AI assistant</h2>
          <ChatBot onContextChange={handleContextChange} />
        </div>
      </div>
      <div className="mt-8">
        <h2 className="text-2xl font-bold mb-4">Knowledge Graph</h2>
        <GraphVisualization recommendedIds={recommendedIds} />
      </div>
    </div>
  );
}

export default App;
