# PRODUCT RECOMMENDER SYSTEM

A knowledge graph-based product recommendation system that combines AI-driven recommendations, PageRank algorithm, and natural language processing to provide personalized product recommendations.

https://github.com/user-attachments/assets/a796a815-5ca5-46dc-a49c-96b3c1641f7a


## Dataset

The system uses the [Fashion Clothing Products Catalog](https://www.kaggle.com/datasets/shivamb/fashion-clothing-products-catalog) from Kaggle. This comprehensive dataset includes:
- Detailed product information
- Multiple product attributes
- Wide range of clothing categories
- Comprehensive brand and style information

### Dataset Characteristics
- Over 10,000 unique fashion products
- Attributes include: brand, gender, color, price, category, and more
- Suitable for building a rich product recommendation knowledge graph

## Features

- **AI-Driven Recommendations**: Uses OpenAI's GPT-3.5 to understand user queries and provide contextual recommendations
- **Knowledge Graph**: Built using Neo4j to represent product relationships and similarities
- **PageRank Algorithm**: Provides additional recommendations based on product importance in the graph
- **Natural Language Interface**: Chat-based interface for natural product discovery
- **Interactive Visualization**: D3.js visualization showing relationships between recommended products

## Technical Implementation

### 1. AI Recommendations
- Natural language query processing
- Context-aware product matching
- Structured response generation
- Integration with OpenAI's GPT-3.5

### 2. PageRank Implementation
Nodes represent products, with edges representing similarities. Edge weights are based on:
- Same brand (0.3 weight)
- Same gender (0.4 weight)
- Same color (0.3 weight)
- Price similarity:
  - 0.2 for <₹200 difference
  - 0.1 for <₹500 difference

### 3. Graph Visualization
- Interactive D3.js visualization with:
  - Color coding:
    * Green: AI recommendations
    * Blue: PageRank recommendations
    * Gray: Other products
  - Node size based on PageRank score
  - Zoom and pan functionality
  - Product details on hover

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 14+
- Neo4j Database
- OpenAI API key
- Kaggle account (to download dataset)

### Backend Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/rcisneros99/AIKnowledgeGraph
   cd AIKnowledgeGraph
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure `.env` file:
   ```
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   OPENAI_API_KEY=your_openai_key
   ```
5. Start the Neo4j Database
   ```
   neo4j start
   neo4j-admin set-initial-password your_password
   neo4j-admin dbms set-initial-password your_password
   ```

5. Start backend (Neo4j database):
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup

1. Navigate to frontend:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start development server:
   ```bash
   npm start
   ```

## Interacting with Neo4j Graph

### Neo4j Browser Visualization

1. Open Neo4j Desktop or Neo4j Browser (Most probably in http://localhost:7474/browser/)
2. Connect to your local database with your Username and Password
3. Use Cypher queries to explore the graph:

   ```cypher
   // View all product nodes
   MATCH (p:Product) RETURN p LIMIT 100

   // Find products by brand
   MATCH (p:Product {brand: 'Nike'}) RETURN p

   // Explore product relationships
   MATCH (p1:Product)-[r:SIMILAR]->(p2:Product) 
   RETURN p1, r, p2 LIMIT 50
   ```

### Interactive Graph Exploration
- Use the Neo4j Browser's visualization tools
- Zoom in/out
- Click and drag nodes
- View node and relationship properties
- Filter and explore connections

### Advanced Graph Analysis
- Use built-in PageRank algorithm
  ```cypher
  CALL algo.pageRank.stream('Product', 'SIMILAR')
  YIELD nodeId, score
  RETURN algo.getNodeById(nodeId).name AS product, score
  ORDER BY score DESC LIMIT 10
  ```

## Usage

1. Open browser to `http://localhost:3000`
2. Use chat interface for natural language queries:
   - "I'm looking for blue men's pants"
   - "Show me women's dresses"
   - "Find casual t-shirts"
3. View recommendations:
   - AI recommendations (green)
   - PageRank recommendations (blue)
4. Explore product relationships in graph visualization
5. View performance metrics for PageRank recommendations

## System Architecture

### Backend (FastAPI)
- Knowledge Graph (Neo4j)
- RAG System with OpenAI
- PageRank Implementation
- Product Recommendations

### Frontend (React)
- Chat Interface
- Product Grid
- Graph Visualization
- Performance Metrics

## Performance Metrics

- **Precision**: Accuracy of PageRank recommendations
- **Recall**: Coverage of relevant products
- **F1 Score**: Balance between precision and recall

## Limitations

- Limited to available product attributes
- Dependent on OpenAI API availability
- Graph visualization performance with large datasets
- Requires periodic dataset updates

## License

MIT License - see LICENSE file for details

## Future Work

- Implement more complex relationship weighting
- Add user interaction tracking
- Expand dataset with more diverse products
- Improve AI recommendation accuracy
