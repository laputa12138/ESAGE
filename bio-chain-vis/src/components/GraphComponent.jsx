import React, { useEffect, useRef } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';

export const GraphComponent = ({ elements, onNodeClick }) => {
    const cyRef = useRef(null);

    const layout = {
        name: 'preset',
        fit: true,
        padding: 50,
        animate: true,
        animationDuration: 500,
    };

    const stylesheet = [
        {
            selector: 'node',
            style: {
                'label': 'data(label)',
                'text-valign': 'bottom',
                'text-halign': 'center',
                'text-margin-y': 8,
                'font-family': 'Inter, sans-serif',
                'font-size': 12,
                'color': '#1E293B', // text-slate-800
                'background-color': '#94A3B8', // slate-400 default
                'width': 40,
                'height': 40,
                'border-width': 2,
                'border-color': '#fff',
                'overlay-opacity': 0,
            }
        },
        {
            selector: 'node.upstream',
            style: {
                'background-color': '#3B82F6', // blue-500
                'border-color': '#DBEAFE', // blue-100
            }
        },
        {
            selector: 'node.midstream',
            style: {
                'background-color': '#F97316', // orange-500 (CTA color)
                'border-color': '#FFEDD5', // orange-100
                'width': 60,
                'height': 60,
                'font-size': 14,
                'font-weight': 'bold',
            }
        },
        {
            selector: 'node.downstream',
            style: {
                'background-color': '#10B981', // green-500 (Example different color)
                'border-color': '#D1FAE5',
            }
        },
        {
            selector: 'edge',
            style: {
                'width': 2,
                'line-color': '#CBD5E1', // slate-300
                'target-arrow-color': '#CBD5E1',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'opacity': 0.8,
            }
        },
        {
            selector: ':selected',
            style: {
                'border-width': 4,
                'border-color': '#2563EB', // primary blue
            }
        }
    ];

    useEffect(() => {
        if (cyRef.current) {
            cyRef.current.on('tap', 'node', (evt) => {
                const node = evt.target;
                onNodeClick(node.id());
            });
        }
    }, []);

    return (
        <CytoscapeComponent
            elements={elements}
            style={{ width: '100%', height: '100%' }}
            layout={layout}
            stylesheet={stylesheet}
            cy={(cy) => { cyRef.current = cy; }}
            className="bg-white/50 backdrop-blur-sm rounded-xl border border-white/20 shadow-inner"
        />
    );
};
