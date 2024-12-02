const ProductCard = ({ product, isRecommended }) => {
  console.log("Rendering product card:", {
    name: product.name,
    type: product.recommendation_type,
    isRecommended
  });

  return (
    <div 
      className={`border rounded-lg shadow-lg p-4 ${
        product.recommendation_type === 'ai' ? 'bg-green-50' :
        product.recommendation_type === 'pagerank' ? 'bg-blue-50' :
        'bg-white'
      }`}
    >
      <h3 className="font-bold text-lg mb-2 text-gray-800">{product.name}</h3>
      <div className="text-sm text-gray-600">
        <p>Brand: {product.brand}</p>
        <p>Gender: {product.gender}</p>
        <p>Price: ₹{product.price}</p>
        <p>Color: {product.color}</p>
        <p>Relevance: {(product.pagerank * 100).toFixed(2)}%</p>
        {product.recommendation_type === 'ai' && (
          <p className="text-green-600 font-semibold mt-2">Recommended by Assistant</p>
        )}
        {product.recommendation_type === 'pagerank' && (
          <p className="text-blue-600 font-semibold mt-2">PageRank Recommendation</p>
        )}
        {product.recommendation_type === 'connected' && (
          <p className="text-indigo-600 font-semibold mt-2">Related Product</p>
        )}
      </div>
    </div>
  );
};

export default ProductCard; 