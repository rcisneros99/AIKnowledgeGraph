from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from .database import Neo4jConnection
from .graph_builder import GraphBuilder
from .rag import RAGAgent

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

neo4j = Neo4jConnection()
graph_builder = GraphBuilder()
rag_agent = RAGAgent()

class ChatMessage(BaseModel):
    message: str

class Product(BaseModel):
    product_id: str
    name: str
    brand: str
    gender: str
    price: float
    color: str
    pagerank: float
    recommendation_type: str = 'other'

@app.on_event("startup")
async def startup_event():
    # Build knowledge graph on startup
    graph_builder.build_knowledge_graph("data/myntra.csv")
    graph_builder.calculate_pagerank()

@app.get("/products/")
async def get_products(recommended_ids: str = None):
    try:
        id_list = recommended_ids.split(',') if recommended_ids else []
        print(f"Processing request for recommended_ids: {id_list}")
        
        # First, clear all recommendation types
        clear_query = """
        MATCH (p:Product)
        SET p.recommendation_type = 'other'
        """
        neo4j.query(clear_query)
        
        # Main recommendation query
        query = """
        MATCH (p:Product)
        WHERE CASE
            WHEN $recommended_ids IS NOT NULL THEN
                p.product_id IN $recommended_ids
            ELSE true
        END
        WITH p,
             CASE 
                 WHEN p.product_id IN $recommended_ids THEN 'ai'
                 ELSE 'other'
             END as recommendation_type,
             p.pagerank as rank
        RETURN p.product_id as product_id,
               p.name as name,
               p.brand as brand,
               p.gender as gender,
               p.price as price,
               p.color as color,
               recommendation_type,
               rank as pagerank
        ORDER BY recommendation_type = 'ai' DESC, rank DESC
        LIMIT 50
        """
        
        results = neo4j.query(query, {"recommended_ids": id_list})
        print(f"Initial AI recommendations: {[r['product_id'] for r in results]}")
        products = [Product(**record) for record in results]
        
        # Update AI recommendations in graph
        if id_list:
            update_ai_query = """
            MATCH (p:Product)
            WHERE p.product_id IN $recommended_ids
            SET p.recommendation_type = 'ai'
            """
            neo4j.query(update_ai_query, {"recommended_ids": id_list})
        
        # Get PageRank recommendations
        if id_list:
            pagerank_query = """
            MATCH (p:Product)
            WHERE NOT p.product_id IN $recommended_ids
            WITH p
            ORDER BY p.pagerank DESC
            LIMIT 10
            RETURN p.product_id as product_id,
                   p.name as name,
                   p.brand as brand,
                   p.gender as gender,
                   p.price as price,
                   p.color as color,
                   'pagerank' as recommendation_type,
                   p.pagerank as pagerank
            """
            pagerank_results = neo4j.query(pagerank_query, {"recommended_ids": id_list})
            print(f"PageRank recommendations: {[r['product_id'] for r in pagerank_results]}")
            products.extend([Product(**record) for record in pagerank_results])
            
            # Update PageRank recommendations in graph
            update_pagerank_query = """
            MATCH (p:Product)
            WHERE p.product_id IN $pagerank_ids
            SET p.recommendation_type = 'pagerank'
            """
            neo4j.query(update_pagerank_query, {
                "pagerank_ids": [r["product_id"] for r in pagerank_results]
            })
            
            # Calculate PageRank performance metrics
            metrics_query = """
            MATCH (p:Product)
            WHERE p.product_id IN $pagerank_ids
            WITH collect(p) as pagerank_recs
            MATCH (p1:Product)-[r:SIMILAR_TO]->(p2:Product)
            WHERE p1 IN pagerank_recs
                AND r.similarity_score >= 0.6
                AND (
                    p1.gender = p2.gender AND 
                    (p1.brand = p2.brand OR p1.color = p2.color)
                )
            WITH pagerank_recs, collect(DISTINCT p2) as relevant_products
            RETURN 
                size(pagerank_recs) as num_recommendations,
                size(relevant_products) as num_relevant,
                size([x IN pagerank_recs WHERE x IN relevant_products]) as true_positives
            """
            metrics_result = neo4j.query(metrics_query, {
                "pagerank_ids": [r["product_id"] for r in pagerank_results]
            })[0]

            num_recommendations = metrics_result['num_recommendations']
            num_relevant = metrics_result['num_relevant']
            true_positives = metrics_result['true_positives']

            precision = true_positives / num_recommendations if num_recommendations > 0 else 0
            recall = true_positives / num_relevant if num_relevant > 0 else 0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            metrics = {
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "num_recommendations": num_recommendations,
                "num_relevant": num_relevant,
                "true_positives": true_positives
            }
        else:
            metrics = None

        # Debug: Print final products list
        print("Final products list:", [
            {
                'id': p.product_id,
                'name': p.name,
                'type': p.recommendation_type
            } for p in products
        ])

        return {
            "products": products,
            "metrics": metrics
        }
    except Exception as e:
        print(f"Error in get_products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/")
async def chat(message: ChatMessage):
    print(f"Processing chat message: {message.message}")
    try:
        response, recommended_products = await rag_agent.get_response(message.message)
        print(f"Got response from RAG agent: {response[:100]}...")
        return {
            "response": response,
            "recommended_products": recommended_products
        }
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph-data/")
async def get_graph_data():
    try:
        # First verify PageRank nodes exist
        verify_query = """
        MATCH (p:Product)
        WHERE p.recommendation_type = 'pagerank'
        RETURN count(p) as count
        """
        verify_result = neo4j.query(verify_query)
        print(f"Found {verify_result[0]['count']} PageRank nodes in database")

        query = """
        // Start with recommended nodes
        MATCH (p:Product)
        WHERE p.recommendation_type IN ['ai', 'pagerank', 'connected']
        WITH p
        
        // Get connected nodes and their relationships
        MATCH (p)-[:SIMILAR_TO*0..2]-(connected:Product)
        WITH p, connected
        
        // Get all relationships between these nodes
        MATCH (p1:Product)-[r:SIMILAR_TO]->(p2:Product)
        WHERE (p1 = p OR p1 = connected)
            AND (p2 = p OR p2 = connected)
            AND r.similarity_score >= 0.5
        ORDER BY p1.pagerank DESC
        RETURN DISTINCT
               p1.product_id as source, 
               p2.product_id as target,
               p1.name as source_name, 
               p1.brand as source_brand, 
               p1.gender as source_gender,
               p1.price as source_price, 
               p1.color as source_color,
               p1.pagerank as source_pagerank,
               p1.recommendation_type as source_type,
               p2.name as p2_name,
               p2.brand as target_brand,
               p2.gender as target_gender,
               p2.price as target_price,
               p2.color as target_color,
               p2.pagerank as target_pagerank,
               p2.recommendation_type as target_type,
               r.similarity_score as similarity_score
        """
        results = neo4j.query(query)
        print("Graph query results - first 5 nodes:")
        for r in results[:5]:
            print(f"Source: {r['source_name']} (type: {r['source_type']}) -> Target: {r['p2_name']} (type: {r['target_type']})")
        print("Graph query results:")
        for r in results[:5]:  # Print first 5 results
            print(f"Source: {r['source_name']} ({r['source_type']}) -> Target: {r['p2_name']} ({r['target_type']})")
        print(f"Graph data - found {len(results)} relationships")
        print("First few nodes with types:", [
            {
                'name': r['source_name'],
                'type': r['source_type'],
                'id': r['source']
            } for r in results[:3]
        ])

        nodes = {}
        links = []
        
        for record in results:
            # Add source node
            if record['source'] not in nodes:
                source_type = record['source_type'] or 'other'
                print(f"Adding source node {record['source_name']} with type {source_type}")
                nodes[record['source']] = {
                    'id': record['source'],
                    'name': record['source_name'],
                    'brand': record['source_brand'],
                    'gender': record['source_gender'],
                    'price': record['source_price'],
                    'color': record['source_color'],
                    'value': record['source_pagerank'],
                    'type': source_type
                }
            
            # Add target node
            if record['target'] not in nodes:
                nodes[record['target']] = {
                    'id': record['target'],
                    'name': record['p2_name'],
                    'brand': record['target_brand'],
                    'gender': record['target_gender'],
                    'price': record['target_price'],
                    'color': record['target_color'],
                    'value': record['target_pagerank'],
                    'type': record['target_type'] or 'other'
                }
            
            links.append({
                'source': record['source'],
                'target': record['target'],
                'similarity_score': record['similarity_score']
            })
        
        print("Node types distribution:", {
            'ai': len([n for n in nodes.values() if n['type'] == 'ai']),
            'pagerank': len([n for n in nodes.values() if n['type'] == 'pagerank']),
            'connected': len([n for n in nodes.values() if n['type'] == 'connected']),
            'other': len([n for n in nodes.values() if n['type'] == 'other'])
        })
        
        return {
            'nodes': list(nodes.values()),
            'links': links
        }
    except Exception as e:
        print(f"Error in graph_data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Welcome to the Product Recommender API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 