import pandas as pd
import networkx as nx
from .database import Neo4jConnection
from concurrent.futures import ThreadPoolExecutor
from functools import partial

class GraphBuilder:
    def __init__(self):
        self.neo4j = Neo4jConnection()

    def create_relationships_batch(self, session, batch_ids):
        session.run("""
            MATCH (p1:Product)
            WHERE p1.product_id IN $batch_ids
            MATCH (p2:Product)
            WHERE p2.product_id > p1.product_id
            AND (
                p1.brand = p2.brand OR
                p1.gender = p2.gender OR
                p1.color = p2.color OR
                abs(p1.price - p2.price) < 500
            )
            WITH p1, p2,
                 CASE WHEN p1.brand = p2.brand THEN 1 ELSE 0 END +
                 CASE WHEN p1.gender = p2.gender THEN 1 ELSE 0 END +
                 CASE WHEN p1.color = p2.color THEN 1 ELSE 0 END +
                 CASE WHEN abs(p1.price - p2.price) < 500 THEN 1 END as similarity_score
            WHERE similarity_score >= 2
            WITH p1, p2, similarity_score
            ORDER BY similarity_score DESC
            LIMIT 5
            CREATE (p1)-[:SIMILAR_TO {
                same_brand: p1.brand = p2.brand,
                same_gender: p1.gender = p2.gender,
                same_color: p1.color = p2.color,
                price_diff: abs(p1.price - p2.price),
                similarity_score: similarity_score
            }]->(p2)
        """, {'batch_ids': batch_ids})

    def build_knowledge_graph(self, csv_path):
        df = pd.read_csv('data/myntra.csv', low_memory=False)
        print(f"Loaded {len(df)} products from CSV")
        
        batch_size = 100
        product_batches = [df[i:i + batch_size] for i in range(0, len(df), batch_size)]
        
        with self.neo4j.driver.session() as session:
            # Clear existing data
            session.run("MATCH (n) DETACH DELETE n")
            print("Cleared existing data from Neo4j")
            
            # Create indices
            session.run("CREATE INDEX product_id IF NOT EXISTS FOR (p:Product) ON (p.product_id)")
            session.run("CREATE INDEX brand IF NOT EXISTS FOR (p:Product) ON (p.brand)")
            session.run("CREATE INDEX gender IF NOT EXISTS FOR (p:Product) ON (p.gender)")
            session.run("CREATE INDEX color IF NOT EXISTS FOR (p:Product) ON (p.color)")
            print("Created indices")
            
            print(f"Processing {len(product_batches)} batches...")
            
            # Process batches
            for batch_num, batch_df in enumerate(product_batches, 1):
                print(f"Processing batch {batch_num}/{len(product_batches)}")
                
                # Create nodes
                with session.begin_transaction() as tx:
                    for _, row in batch_df.iterrows():
                        tx.run("""
                            CREATE (p:Product {
                                product_id: $product_id,
                                name: $name,
                                brand: $brand,
                                gender: $gender,
                                price: $price,
                                color: $color,
                                description: $description,
                                num_images: $num_images
                            })
                        """, {
                            'product_id': str(row['ProductID']),
                            'name': str(row['ProductName']),
                            'brand': str(row['ProductBrand']),
                            'gender': str(row['Gender']),
                            'price': float(row['Price (INR)']),
                            'color': str(row['PrimaryColor']),
                            'description': str(row['Description']).lower(),
                            'num_images': int(row['NumImages'])
                        })
                
                # Create relationships
                with session.begin_transaction() as tx:
                    tx.run("""
                        MATCH (p1:Product)
                        WHERE p1.product_id IN $batch_ids
                        MATCH (p2:Product)
                        WHERE p2.product_id > p1.product_id
                        AND p1.gender = p2.gender
                        AND (
                            (p1.brand = p2.brand AND abs(p1.price - p2.price) < 1000) OR
                            (p1.color = p2.color AND abs(p1.price - p2.price) < 500) OR
                            (abs(p1.price - p2.price) < 200)
                        )
                        WITH p1, p2,
                             CASE WHEN p1.brand = p2.brand THEN 2 ELSE 0 END +
                             CASE WHEN p1.color = p2.color THEN 1 ELSE 0 END +
                             CASE WHEN abs(p1.price - p2.price) < 200 THEN 2
                                  WHEN abs(p1.price - p2.price) < 500 THEN 1
                                  ELSE 0 END as similarity_score
                        WHERE similarity_score >= 2
                        WITH p1, p2, similarity_score
                        ORDER BY similarity_score DESC
                        LIMIT 5
                        CREATE (p1)-[:SIMILAR_TO {
                            same_brand: p1.brand = p2.brand,
                            same_gender: p1.gender = p2.gender,
                            same_color: p1.color = p2.color,
                            price_diff: abs(p1.price - p2.price),
                            similarity_score: similarity_score
                        }]->(p2)
                    """, {
                        'batch_ids': batch_df['ProductID'].astype(str).tolist()
                    })

    def calculate_pagerank(self):
        print("Starting PageRank calculation...")
        # First, set default pagerank for all products
        with self.neo4j.driver.session() as session:
            session.run("""
                MATCH (p:Product)
                SET p.pagerank = 0.15  // Default value
            """)

        # Get the graph structure with weights
        query = """
        MATCH (p1:Product)-[r:SIMILAR_TO]->(p2:Product)
        WITH p1, p2, r
        MATCH (p1)-[out:SIMILAR_TO]->()
        WITH p1, p2, r, count(out) as out_degree
        MATCH (p2)<-[in:SIMILAR_TO]-()
        WITH p1, p2, r, out_degree, count(in) as in_degree
        RETURN p1.product_id as source, 
               p2.product_id as target,
               p1.gender as source_gender,
               p2.gender as target_gender,
               p1.color = p2.color as same_color,
               p1.brand = p2.brand as same_brand,
               abs(p1.price - p2.price) as price_diff,
               out_degree, in_degree
        """
        results = self.neo4j.query(query)
        
        # Create NetworkX graph with weighted edges
        G = nx.DiGraph()
        
        # Track node connectivity
        node_connections = {}
        
        for record in results:
            source = record['source']
            target = record['target']
            
            # Update node connectivity
            if source not in node_connections:
                node_connections[source] = {'out': 0, 'in': 0}
            if target not in node_connections:
                node_connections[target] = {'out': 0, 'in': 0}
            node_connections[source]['out'] += 1
            node_connections[target]['in'] += 1
            
            # Calculate edge weight based on multiple factors
            weight = 0.0
            if record['source_gender'] == record['target_gender']:
                weight += 0.4
            if record['same_color']:
                weight += 0.3
            if record['same_brand']:
                weight += 0.3
            if record['price_diff'] < 200:
                weight += 0.2
            elif record['price_diff'] < 500:
                weight += 0.1
            
            # Adjust weight based on node connectivity
            connectivity_factor = (record['out_degree'] + record['in_degree']) / 10.0
            weight *= (1 + connectivity_factor)
            
            G.add_edge(source, target, weight=weight)
        
        # Calculate personalized PageRank with damping factor adjustment
        personalization = {}
        for node in G.nodes():
            conn = node_connections.get(node, {'out': 0, 'in': 0})
            # Increase importance of well-connected nodes
            personalization[node] = 1 + (conn['out'] + conn['in']) / 5.0  # Increased factor
        
        pagerank = nx.pagerank(G, alpha=0.9,  # Increased damping factor
                              weight='weight',
                              personalization=personalization,
                              max_iter=100)  # Increased iterations
        
        # Update Neo4j with normalized PageRank scores
        max_score = max(pagerank.values()) if pagerank else 1.0
        with self.neo4j.driver.session() as session:
            for node_id, score in pagerank.items():
                normalized_score = score / max_score
                session.run("""
                    MATCH (p:Product {product_id: $id})
                    SET p.pagerank = $score
                """, {'id': node_id, 'score': normalized_score})

        print("PageRank calculation completed")

        # Verify PageRank values
        verify_query = """
        MATCH (p:Product)
        RETURN min(p.pagerank) as min, max(p.pagerank) as max, avg(p.pagerank) as avg
        """
        results = self.neo4j.query(verify_query)
        print(f"PageRank stats: {results[0]}") 