import React, { useState, useEffect } from 'react';
import ProductCard from './ProductCard';

const ProductGrid = ({ context }) => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    setLoading(true);
    console.log("Context changed to:", context);
    let url = `http://localhost:8000/products/`;
    if (context && context.startsWith('recommended:')) {
      const recommendedIds = context.split(':')[1];
      url += `?recommended_ids=${recommendedIds}`;
    }
    console.log("Fetching products from:", url);
    fetch(url)
      .then(response => response.json())
      .then(data => {
        console.log("Received products:", data);
        if (!data.products) {
          console.error("No products array in response:", data);
          setProducts([]);
        } else {
          console.log("Setting products:", data.products.map(p => ({
            name: p.name,
            type: p.recommendation_type
          })));
          setProducts(data.products);
          setMetrics(data.metrics);
        }
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching products:', error);
        setProducts([]);
        setMetrics(null);
        setLoading(false);
      });
  }, [context]);

  return (
    <div className="grid grid-cols-1 gap-4 p-4">
      {loading ? (
        <div className="col-span-3 text-center text-gray-500">Loading...</div>
      ) : products.length === 0 ? (
        <div className="col-span-3 text-center text-gray-500">No products found</div>
      ) : (
        <>
          {/* AI Recommendations */}
          <div className="mb-8">
            <h2 className="text-xl font-bold mb-4">AI Recommendations</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {products
                .filter(p => p.recommendation_type === 'ai')
                .map(product => (
                  <ProductCard key={product.product_id} product={product} isRecommended={true} />
                ))}
            </div>
          </div>
          
          {/* PageRank Recommendations */}
          <div className="mb-8">
            <h2 className="text-xl font-bold mb-4">PageRank Recommendations</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {products
                .filter(p => p.recommendation_type === 'pagerank')
                .map(product => (
                  <ProductCard key={product.product_id} product={product} isRecommended={false} />
                ))}
            </div>
          </div>

          {/* PageRank Performance Metrics */}
          {metrics && (
            <div className="mt-8 bg-white p-6 rounded-lg shadow-lg">
              <h2 className="text-xl font-bold mb-4">PageRank Performance Metrics</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                <div>
                  <h3 className="text-lg font-semibold text-gray-700">Precision</h3>
                  <p className="text-3xl font-bold text-blue-600">
                    {(metrics.precision * 100).toFixed(1)}%
                  </p>
                  <p className="text-sm text-gray-500">
                    Accuracy of PageRank recommendations
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-700">Recall</h3>
                  <p className="text-3xl font-bold text-blue-600">
                    {(metrics.recall * 100).toFixed(1)}%
                  </p>
                  <p className="text-sm text-gray-500">
                    Coverage of relevant products
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-700">F1 Score</h3>
                  <p className="text-3xl font-bold text-blue-600">
                    {(metrics.f1_score * 100).toFixed(1)}%
                  </p>
                  <p className="text-sm text-gray-500">
                    Balance of precision and recall
                  </p>
                </div>
              </div>
              <div className="mt-4 text-sm text-gray-600">
                <p>Based on {metrics.num_recommendations} recommendations and {metrics.num_relevant} relevant products</p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ProductGrid;
