import { useCallback, useEffect, useRef, useState } from 'react';
import 'leaflet/dist/leaflet.css';
import { ChatPanel } from './components/ChatPanel';
import { MarineMap } from './components/MarineMap';
import { RiskDashboard } from './components/RiskDashboard';
import { HistoricalDashboard } from './components/HistoricalDashboard';
import { AgentTrace } from './components/AgentTrace';
import { sendMessage, OrcaWebSocket } from './services/api';
import type { ChatMessage, OrcaResponse, WSEvent, AgentTrace as AgentTraceType, Location } from './types';

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentResponse, setCurrentResponse] = useState<OrcaResponse | null>(null);
  const [agentProgress, setAgentProgress] = useState<AgentTraceType[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null);
  const [conversationId, setConversationId] = useState<string>('');
  const [showTrace, setShowTrace] = useState(false);
  const wsRef = useRef<OrcaWebSocket | null>(null);

  // Connect WebSocket
  useEffect(() => {
    const ws = new OrcaWebSocket((event: WSEvent) => {
      if (event.type === 'agent_progress') {
        setAgentProgress(prev => {
          const existing = prev.findIndex(a => a.agent_name === event.agent);
          const trace: AgentTraceType = {
            agent_name: event.agent || '',
            status: event.status || 'running',
            message: event.message,
            data: event.data as Record<string, unknown> | undefined,
          };
          if (existing >= 0) {
            const updated = [...prev];
            updated[existing] = trace;
            return updated;
          }
          return [...prev, trace];
        });
      }
    });
    ws.connect();
    wsRef.current = ws;
    return () => ws.disconnect();
  }, []);

  const handleSend = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setAgentProgress([]);
    setShowTrace(true);

    try {
      const response = await sendMessage({
        message: text,
        location: selectedLocation || undefined,
        conversation_id: conversationId || undefined,
      });

      const orcaMsg: ChatMessage = {
        id: `orca-${Date.now()}`,
        role: 'orca',
        content: response.recommendation,
        timestamp: response.timestamp,
        response,
      };

      setMessages(prev => [...prev, orcaMsg]);
      setCurrentResponse(response);
      setConversationId(response.conversation_id);
      setAgentProgress(response.agent_traces);
    } catch (error) {
      const errMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'orca',
        content: `⚠ Connection error: Make sure the backend is running on port 8000.\n\n\`\`\`\n${error}\n\`\`\``,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, selectedLocation, conversationId]);

  const handleMapClick = useCallback((lat: number, lng: number) => {
    setSelectedLocation({ lat, lng, name: `${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E` });
  }, []);

  return (
    <div className="h-screen w-full flex flex-col bg-ocean-950 overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-ocean-600/30 bg-ocean-900/80 backdrop-blur-md z-50">
        <div className="flex items-center gap-3">
          <span className="text-3xl">🐋</span>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-teal-accent to-blue-accent bg-clip-text text-transparent">
              ORCA Marine Intelligence
            </h1>
            <p className="text-xs text-ocean-400">Agentic AI · Multi-Agent Decision System</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {selectedLocation && (
            <div className="text-xs text-ocean-400 bg-ocean-800/60 px-3 py-1.5 rounded-full border border-ocean-600/30">
              📍 {selectedLocation.name}
            </div>
          )}
          <div className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full bg-green-accent animate-pulse"></span>
            <span className="text-ocean-400">Live Data</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel — Chat */}
        <div className="w-[380px] min-w-[380px] border-r border-ocean-600/30 flex flex-col bg-ocean-900/50">
          <ChatPanel
            messages={messages}
            isLoading={isLoading}
            onSend={handleSend}
            onShowTrace={() => setShowTrace(!showTrace)}
            agentProgress={agentProgress}
          />
        </div>

        {/* Center — Map + Bottom Panels */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Map */}
          <div className="flex-1 relative overflow-hidden">
            <MarineMap
              mapData={currentResponse?.map_data || null}
              onMapClick={handleMapClick}
              selectedLocation={selectedLocation}
            />

            {/* Floating Risk Badge */}
            {currentResponse?.risk_score && (
              <div className="absolute top-4 right-4 z-[1000] animate-slide-up">
                <div className="glass-panel px-4 py-3 flex items-center gap-3">
                  <div
                    className="text-3xl font-black font-mono"
                    style={{ color: currentResponse.risk_score.risk_color }}
                  >
                    {currentResponse.risk_score.final_score}
                  </div>
                  <div>
                    <div className="text-sm font-semibold" style={{ color: currentResponse.risk_score.risk_color }}>
                      {currentResponse.risk_score.risk_emoji} {currentResponse.risk_score.risk_label}
                    </div>
                    <div className="text-xs text-ocean-400">
                      Primary: {currentResponse.risk_score.primary_hazard}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Bottom Panel — Risk Dashboard / Agent Trace */}
          <div className="h-[240px] min-h-[240px] border-t border-ocean-600/30 flex overflow-hidden">
            {showTrace && agentProgress.length > 0 ? (
              <div className="w-[400px] min-w-[400px] border-r border-ocean-600/30 overflow-y-auto p-3">
                <AgentTrace traces={agentProgress} />
              </div>
            ) : null}
            <div className="flex-1 overflow-x-auto overflow-y-hidden custom-scrollbar">
              {currentResponse?.historical_report ? (
                <HistoricalDashboard historicalReport={currentResponse.historical_report} />
              ) : (
                <RiskDashboard
                  riskScore={currentResponse?.risk_score || null}
                  weatherReport={currentResponse?.weather_report || null}
                  oceanReport={currentResponse?.ocean_report || null}
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
