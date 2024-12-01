from openai import OpenAI
import os
from .database import Neo4jConnection

class RAGAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.neo4j = Neo4jConnection()

    def get_context(self, query):
        print(f"Getting context for query: {query}")
        words = query.lower().split()
        
        print(f"Extracted words: {words}")
        # Extract key attributes
        gender = next((w for w in words if w in ['men', 'women', 'boys', 'girls']), None)
        color = next((w for w in words if w in ['red', 'blue', 'black', 'white']), None)
        product_type = next((w for w in words if w in ['bra', 'bras', 'shirt', 'shirts', 't-shirt', 't-shirts', 'pants', 'jeans', 'dress']), None)
        
        # Also check for compound words
        if not product_type and 't' in words and 'shirt' in words:
            product_type = 'shirt'
        
        print(f"Extracted attributes - gender: {gender}, color: {color}, type: {product_type}")
        
        cypher_query = """
        // First find matching products
        MATCH (p:Product)
        WHERE 
            ($gender IS NULL OR toLower(p.gender) = $gender)
            AND ($color IS NULL OR toLower(p.color) = $color)
            AND ($type IS NULL OR 
                 toLower(p.name) CONTAINS $type OR 
                 toLower(p.description) CONTAINS $type)
        
        // Get similarity and collaborative data
        WITH p
        OPTIONAL MATCH (p)-[r:SIMILAR_TO]->(similar)
        WHERE r.similarity_score >= 2
        
        // Aggregate product data
        WITH p,
             collect(similar) as similar_items,
             count(similar) as num_similar,
             p.pagerank as base_rank
        
        // Calculate final score
        WITH p,
             similar_items,
             (base_rank * 0.4 +                    // PageRank component
              toFloat(num_similar)/10.0 * 0.6) as score    // Similarity component
        
        ORDER BY score DESC
        LIMIT 5
        
        // Return full product details
        RETURN 
            p.product_id as id,
            p.name as name,
            p.brand as brand,
            p.gender as gender,
            p.price as price,
            p.color as color,
            score as relevance,
            [item in similar_items | item.name] as similar_names
        """
        
        try:
            results = self.neo4j.query(cypher_query, {
                "gender": gender.lower() if gender else None,
                "color": color.lower() if color else None,
                "type": product_type.lower() if product_type else None
            })
            
            if not results:
                return "No specific products found matching your criteria.", []
            
            context = "Here are some relevant products I found:\n\n"
            recommended_products = []
            total_relevance = 0
            
            for r in results:
                context += f"• {r['name']}\n"
                context += f"  Brand: {r['brand']}\n"
                context += f"  Gender: {r['gender']}\n"
                context += f"  Price: ₹{r['price']}\n"
                context += f"  Color: {r['color']}\n"
                if r['similar_names']:
                    context += f"  Similar items: {', '.join(r['similar_names'][:2])}\n"
                context += "\n"
                
                recommended_products.append(r['id'])
                total_relevance += r['relevance']
            
            if results:
                avg_relevance = total_relevance / len(results)
                context += f"\nRecommendation confidence: {avg_relevance:.2%}\n"
            
            return context, recommended_products

        except Exception as e:
            print(f"Error getting context: {str(e)}")
            return "I encountered an error while searching for products.", []

    async def get_response(self, message: str):
        try:
            context, recommended_products = self.get_context(message)
            
            prompt = f"""Based on the user's request: "{message}", I found these products:

{self._format_products(context)}

Please provide a helpful response recommending these products. 
Format your response in a clear, structured way:
1. Start with a brief introduction
2. List each recommended product with its key features
3. Add any relevant styling suggestions or complementary items
"""
            
            response = await self.get_openai_response(prompt)
            return response, recommended_products
        except Exception as e:
            print(f"Error in get_response: {str(e)}")
            raise

    def _format_products(self, products):
        formatted = []
        # Split the context string to get individual product entries
        product_entries = products.split("• ")[1:]  # Skip the first empty part
        for entry in product_entries:
            lines = entry.strip().split("\n")
            name = lines[0]
            details = {}
            for line in lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    details[key.strip()] = value.strip()
            formatted.append(f"""
- {name}
  * Brand: {details.get('Brand', 'N/A')}
  * Gender: {details.get('Gender', 'N/A')}
  * Price: {details.get('Price', 'N/A')}
  * Color: {details.get('Color', 'N/A')}
""")
        return "\n".join(formatted)

    async def get_openai_response(self, prompt):
        system_prompt = """You are a helpful shopping assistant..."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": prompt},
        ]

        print("Sending request to OpenAI")
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        print("Got response from OpenAI")
        return response.choices[0].message.content