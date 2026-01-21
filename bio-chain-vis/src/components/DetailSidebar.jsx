import React from 'react';
import { GlassCard } from './GlassCard';
import { X, ChevronRight, CheckCircle2, FlaskConical, Building2, FileText, ArrowRightLeft } from 'lucide-react';

export const DetailSidebar = ({ nodeId, data, onClose }) => {
    if (!nodeId) return null;

    const details = data.node_details[nodeId] || { entity_name: nodeId, description: 'No detailed information available.' };

    return (
        <div className="fixed right-0 top-0 h-full w-96 p-4 z-50">
            <GlassCard className="h-full flex flex-col overflow-hidden !p-0">
                {/* Header */}
                <div className="p-6 border-b border-white/10 flex justify-between items-start bg-white/40">
                    <div>
                        <h2 className="text-xl font-bold text-slate-800">{details.entity_name}</h2>
                        <div className="text-xs font-semibold text-primary mt-1 uppercase tracking-wider">Node Details</div>
                    </div>
                    <button onClick={onClose} className="p-1 hover:bg-black/5 rounded-full transition-colors">
                        <X size={20} className="text-slate-500" />
                    </button>
                </div>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8">

                    {/* Description */}
                    <div className="text-slate-600 leading-relaxed">
                        {details.description}
                    </div>

                    {/* Key Technologies */}
                    {details.key_technologies && details.key_technologies.length > 0 && (
                        <div>
                            <h3 className="flex items-center text-sm font-semibold text-slate-700 mb-3">
                                <FlaskConical size={16} className="mr-2 text-cta" /> Key Technologies
                            </h3>
                            <div className="flex flex-wrap gap-2">
                                {details.key_technologies.map((tech, i) => (
                                    <span key={i} className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-md border border-blue-100">
                                        {tech}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Representative Companies */}
                    {details.representative_companies && details.representative_companies.length > 0 && (
                        <div>
                            <h3 className="flex items-center text-sm font-semibold text-slate-700 mb-3">
                                <Building2 size={16} className="mr-2 text-cta" /> Companies
                            </h3>
                            <ul className="space-y-2">
                                {details.representative_companies.map((comp, i) => (
                                    <li key={i} className="flex items-center text-sm text-slate-600 bg-slate-50 p-2 rounded-lg">
                                        <div className="w-1.5 h-1.5 rounded-full bg-secondary mr-2" />
                                        {comp}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Inputs/Outputs */}
                    {(details.input_elements || details.output_products) && (
                        <div>
                            <h3 className="flex items-center text-sm font-semibold text-slate-700 mb-3">
                                <ArrowRightLeft size={16} className="mr-2 text-cta" /> Flow
                            </h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                                    <span className="text-xs font-medium text-slate-500 block mb-2">Inputs</span>
                                    {details.input_elements?.map((item, i) => (
                                        <div key={i} className="text-xs text-slate-700 mb-1">• {item}</div>
                                    )) || <span className="text-xs text-slate-400">-</span>}
                                </div>
                                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                                    <span className="text-xs font-medium text-slate-500 block mb-2">Outputs</span>
                                    {details.output_products?.map((item, i) => (
                                        <div key={i} className="text-xs text-slate-700 mb-1">• {item}</div>
                                    )) || <span className="text-xs text-slate-400">-</span>}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Evidence Details (Traceability) */}
                    {details.evidence_details && (
                        <div>
                            <h3 className="flex items-center text-sm font-semibold text-slate-700 mb-3">
                                <FileText size={16} className="mr-2 text-cta" /> Evidence Traceability
                            </h3>
                            <div className="space-y-3">
                                {/*  Simplified evidence display logic - looping through categories first */}
                                {['input_elements', 'output_products', 'key_technologies', 'representative_companies'].map(category => {
                                    const categoryEvidence = details.evidence_details[category];
                                    if (!categoryEvidence) return null;
                                    return Object.entries(categoryEvidence).map(([key, evDetail]) => (
                                        <div key={`${category}-${key}`} className="bg-orange-50/50 border border-orange-100 p-3 rounded-lg text-xs">
                                            <div className="font-semibold text-orange-800 mb-1">{key}</div>
                                            <div className="text-slate-600 italic mb-2">"{evDetail.key_evidence || 'Evidence text not available'}"</div>
                                            <div className="flex justify-between text-slate-400 text-[10px]">
                                                <span>Score: {evDetail.score?.toFixed(2)}</span>
                                                <span className="truncate max-w-[120px]" title={evDetail.source_id}>{evDetail.source_id}</span>
                                            </div>
                                        </div>
                                    ));
                                })}
                            </div>
                        </div>
                    )}

                </div>
            </GlassCard>
        </div>
    );
};
