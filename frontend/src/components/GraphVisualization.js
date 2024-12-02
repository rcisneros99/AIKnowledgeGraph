import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

const GraphVisualization = ({ recommendedIds = [] }) => {
  const svgRef = useRef();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchAndRenderGraph = async () => {
      setLoading(true);
      try {
        const response = await fetch('http://localhost:8000/graph-data/');
        const data = await response.json();
        
        // Debug: Log initial data
        console.log('Initial data nodes with pagerank type:', 
          data.nodes.filter(n => n.recommendation_type === 'pagerank')
        );

        const width = 1000;
        const height = 800;
        
        // Color scales
        const genderColorScale = d3.scaleOrdinal()
          .domain(['Men', 'Women', 'Boys', 'Girls', 'Unisex'])
          .range(['#4169e1', '#ff69b4', '#32cd32', '#ff1493', '#9370db']);

        const nodeColorScale = d3.scaleOrdinal()
          .domain(['recommended', 'pagerank', 'connected', 'other'])
          .range(['#22c55e', '#3b82f6', '#93c5fd', '#e5e7eb']);

        // Debug: Log color scale
        console.log('Color scale test:', {
          recommended: nodeColorScale('recommended'),
          pagerank: nodeColorScale('pagerank'),
          connected: nodeColorScale('connected'),
          other: nodeColorScale('other')
        });

        // Clear previous content
        d3.select(svgRef.current).selectAll("*").remove();

        const svg = d3.select(svgRef.current)
          .attr('width', width)
          .attr('height', height)
          .attr('viewBox', [0, 0, width, height])
          .attr('style', 'max-width: 100%; height: auto; background-color: white;');

        // Add legend
        const legend = svg.append('g')
          .attr('class', 'legend')
          .attr('transform', `translate(${width - 180}, 20)`);

        const legendItems = [
          { label: 'AI Recommended', color: '#22c55e' },
          { label: 'PageRank', color: '#3b82f6' },
          { label: 'Other', color: '#e5e7eb' }
        ];

        legendItems.forEach((item, i) => {
          const legendRow = legend.append('g')
            .attr('transform', `translate(0, ${i * 25})`);

          legendRow.append('circle')
            .attr('cx', 10)
            .attr('cy', 10)
            .attr('r', 6)
            .style('fill', item.color)
            .style('stroke', '#666')
            .style('stroke-width', 1);

          legendRow.append('text')
            .attr('x', 25)
            .attr('y', 15)
            .text(item.label)
            .style('font-size', '12px')
            .style('fill', '#666');
        });

        const g = svg.append('g');

        // Add zoom behavior
        const zoom = d3.zoom()
          .scaleExtent([0.1, 4])  // Allow zoom from 0.1x to 4x
          .on('zoom', (event) => {
            g.attr('transform', event.transform);
          });

        svg.call(zoom);

        // Set initial zoom level
        svg.call(zoom.transform, d3.zoomIdentity
          .translate(width/2, height/2)
          .scale(0.8)
          .translate(-width/2, -height/2));

        // Process nodes to mark recommended and connected
        const recommendedSet = new Set(recommendedIds);
        const pagerankSet = new Set(
          data.nodes
            .filter(n => n.type === 'pagerank' || n.recommendation_type === 'pagerank')
            .map(n => n.id)
        );
        console.log('PageRank nodes:', 
          data.nodes
            .filter(n => n.recommendation_type === 'pagerank')
            .map(n => n.name)
        );

        const connectedSet = new Set();
        
        data.links.forEach(link => {
          if (recommendedSet.has(link.source.id)) {
            connectedSet.add(link.target.id);
          }
          if (recommendedSet.has(link.target.id)) {
            connectedSet.add(link.source.id);
          }
          if (pagerankSet.has(link.source.id)) {
            connectedSet.add(link.target.id);
          }
          if (pagerankSet.has(link.target.id)) {
            connectedSet.add(link.source.id);
          }
        });
        
        // Debug: Log sets
        console.log('Sets:', {
          recommended: Array.from(recommendedSet),
          pagerank: Array.from(pagerankSet),
        });

        data.nodes.forEach(node => {
          const originalType = node.recommendation_type;
          if (recommendedSet.has(node.id)) {
            node.type = 'recommended';
          } 
          else if (pagerankSet.has(node.id) || node.recommendation_type === 'pagerank') {
            node.type = 'pagerank';
          }
          else if (connectedSet.has(node.id)) {
            node.type = 'connected';
          } else {
            node.type = 'other';
          }
          console.log(`Node ${node.name}: ${originalType} -> ${node.type}`);
        });

        // Enhanced force simulation
        const simulation = d3.forceSimulation(data.nodes)
          .force('link', d3.forceLink(data.links).id(d => d.id))
          .force('charge', d3.forceManyBody().strength(-100))
          .force('center', d3.forceCenter(width / 2, height / 2))
          .force('collision', d3.forceCollide().radius(20))
          .force('x', d3.forceX(width / 2).strength(0.1))
          .force('y', d3.forceY(height / 2).strength(0.1));

        // Add links
        const links = g.append('g')
          .selectAll('line')
          .data(data.links)
          .join('line')
          .style('stroke', '#999')
          .style('stroke-opacity', 0.6)
          .style('stroke-width', d => Math.sqrt(d.similarity_score) * 2);

        // Add nodes
        const nodes = g.append('g')
          .selectAll('circle')
          .data(data.nodes)
          .join('circle')
          .attr('r', d => {
            const baseSize = Math.max(8, d.value * 20);
            if (d.type === 'recommended') return baseSize * 1.1;
            if (d.type === 'pagerank') return baseSize * 1.1;
            if (d.type === 'connected') return baseSize * 1.05;
            return baseSize;
          })
          .style('fill', d => nodeColorScale(d.type))
          .style('stroke', d => genderColorScale(d.gender))
          .style('stroke-width', d => {
            return 1.5;
          })
          .style('cursor', 'pointer')
          .on('mouseover', (event, d) => {
            // Show tooltip
            const tooltip = d3.select('body').append('div')
              .attr('class', 'tooltip')
              .style('position', 'absolute')
              .style('background', 'white')
              .style('padding', '10px')
              .style('border', '1px solid #ddd')
              .style('border-radius', '5px')
              .style('pointer-events', 'none')
              .style('opacity', 0);

            tooltip.transition()
              .duration(200)
              .style('opacity', .9);

            tooltip.html(`
              <strong>${d.name}</strong><br/>
              Brand: ${d.brand}<br/>
              Gender: ${d.gender}<br/>
              Price: ₹${d.price}<br/>
              Color: ${d.color}
            `)
              .style('left', (event.pageX + 10) + 'px')
              .style('top', (event.pageY - 28) + 'px');
          })
          .on('mouseout', () => {
            d3.selectAll('.tooltip').remove();
          });

        // Update positions
        simulation.on('tick', () => {
          links
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

          nodes
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);
        });

      } catch (error) {
        console.error('Error fetching graph data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAndRenderGraph();
  }, [recommendedIds]);

  return (
    <div className="border rounded-lg shadow-lg bg-white p-4">
      {loading && (
        <div className="text-center text-gray-500">Loading graph...</div>
      )}
      <svg ref={svgRef} className="w-full h-full"></svg>
    </div>
  );
};

export default GraphVisualization;
