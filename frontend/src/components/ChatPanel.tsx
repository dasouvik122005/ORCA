import { useEffect, useRef, useState } from 'react';
import { Send, Brain, Loader2 } from 'lucide-react';
import type { AgentTrace as AgentTraceType, ChatMessage } from '../types';

interface ChatPanelProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSend: (text: string) => void;
  onShowTrace: () => void;
  agentProgress: AgentTraceType[];
}

const SUGGESTIONS = [
  'Is it safe to go fishing tomorrow morning from Digha?',
  'কাল সকালে দীঘা থেকে মাছ ধরতে যাওয়া কি নিরাপদ?',
  'Where is the nearest fishing zone from Paradip?',
  'What is the safest route from Chennai to the fishing zone?',
];

export function ChatPanel({ messages, isLoading, onSend, onShowTrace, agentProgress }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, agentProgress]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onSend(input.trim());
      setInput('');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="p-4 border-b border-ocean-600/30">
        <h2 className="text-sm font-semibold text-teal-accent flex items-center gap-2">
          <span className="text-lg">💬</span> Chat with ORCA
        </h2>
        <p className="text-xs text-ocean-400 mt-0.5">English · हिंदी · বাংলা</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="animate-fade-in">
            <div className="text-center mb-6 mt-4">
              <span className="text-5xl block mb-3">🐋</span>
              <h3 className="text-lg font-semibold text-ocean-400">Welcome to ORCA</h3>
              <p className="text-xs text-ocean-500 mt-1 max-w-[280px] mx-auto">
                Ask me about marine safety, fishing zones, or safe routes. I understand English, Hindi, and Bengali.
              </p>
            </div>
            <div className="space-y-2">
              <p className="text-xs text-ocean-500 font-medium uppercase tracking-wider">Try asking:</p>
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => onSend(s)}
                  className="block w-full text-left text-xs p-3 rounded-xl bg-ocean-800/40 border border-ocean-600/20 text-ocean-400 hover:bg-ocean-700/40 hover:text-teal-accent hover:border-teal-accent/30 transition-all duration-200"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`animate-slide-up ${msg.role === 'user' ? 'flex justify-end' : ''}`}
          >
            {msg.role === 'user' ? (
              <div className="max-w-[85%] bg-teal-accent/15 border border-teal-accent/30 rounded-2xl rounded-tr-md px-4 py-2.5">
                <p className="text-sm text-teal-accent/90">{msg.content}</p>
              </div>
            ) : (
              <div className="max-w-[95%]">
                <div className="bg-ocean-800/60 border border-ocean-600/20 rounded-2xl rounded-tl-md px-4 py-3">
                  {/* Recommendation highlight */}
                  {msg.response?.risk_score && (
                    <div
                      className="flex items-center gap-2 mb-2 px-3 py-1.5 rounded-lg text-xs font-semibold"
                      style={{
                        backgroundColor: msg.response.risk_score.risk_color + '15',
                        color: msg.response.risk_score.risk_color,
                        borderLeft: `3px solid ${msg.response.risk_score.risk_color}`,
                      }}
                    >
                      <span className="text-base">{msg.response.risk_score.risk_emoji}</span>
                      {msg.response.risk_score.risk_label} — Score: {msg.response.risk_score.final_score}/100
                    </div>
                  )}

                  <div className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                    {msg.response?.explanation || msg.content}
                  </div>

                  {/* Show reasoning button */}
                  {msg.response && (
                    <button
                      onClick={onShowTrace}
                      className="mt-3 flex items-center gap-1.5 text-xs text-teal-accent/70 hover:text-teal-accent transition-colors"
                    >
                      <Brain size={14} />
                      Show ORCA's Reasoning
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Loading: Agent Progress */}
        {isLoading && (
          <div className="animate-slide-up">
            <div className="bg-ocean-800/40 border border-ocean-600/20 rounded-2xl px-4 py-3">
              <div className="flex items-center gap-2 text-teal-accent text-xs font-medium mb-2">
                <Loader2 size={14} className="animate-spin" />
                ORCA is analyzing...
              </div>
              <div className="space-y-1.5">
                {agentProgress.map((agent, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span>
                      {agent.status === 'completed' ? '✅' :
                       agent.status === 'running' ? '⏳' :
                       agent.status === 'error' ? '❌' : '⏸'}
                    </span>
                    <span className={agent.status === 'completed' ? 'text-ocean-400' : 'text-slate-300'}>
                      {agent.agent_name}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEnd} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-ocean-600/30">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask ORCA anything..."
            disabled={isLoading}
            className="flex-1 bg-ocean-800/60 border border-ocean-600/30 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder:text-ocean-500 focus:outline-none focus:border-teal-accent/50 focus:ring-1 focus:ring-teal-accent/20 transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-teal-accent/15 border border-teal-accent/30 text-teal-accent rounded-xl px-4 hover:bg-teal-accent/25 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <Send size={16} />
          </button>
        </div>
      </form>
    </div>
  );
}
