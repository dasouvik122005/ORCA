/* ORCA Frontend Types — Mirrors backend Pydantic schemas */

export interface Location {
  lat: number;
  lng: number;
  name?: string;
}

export interface UserQuery {
  message: string;
  location?: Location;
  datetime_target?: string;
  conversation_id?: string;
}

export type Intent = 'SAFETY_CHECK' | 'PFZ_DISCOVERY' | 'ROUTE_PLANNING' | 'EXPLANATION' | 'GENERAL';
export type RiskLevel = 'safe' | 'caution' | 'high_risk' | 'extreme_risk';
export type Language = 'en' | 'hi' | 'bn';
export type AgentStatusType = 'pending' | 'running' | 'completed' | 'error';

export interface AgentTrace {
  agent_name: string;
  status: AgentStatusType;
  message: string;
  data?: Record<string, unknown>;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
}

export interface WeatherReport {
  wind_speed_kmh?: number;
  wind_direction_deg?: number;
  wind_gusts_kmh?: number;
  temperature_c?: number;
  feels_like_c?: number;
  humidity_pct?: number;
  rain_probability_pct?: number;
  rainfall_mm?: number;
  visibility_km?: number;
  cloud_cover_pct?: number;
  lightning_risk?: string;
  cyclone_alert?: string;
  weather_description?: string;
  alerts: string[];
  data_source: string;
}

export interface OceanReport {
  wave_height_m?: number;
  swell_wave_height_m?: number;
  wind_wave_height_m?: number;
  wave_period_s?: number;
  wave_direction_deg?: number;
  swell_wave_period_s?: number;
  ocean_current_velocity_ms?: number;
  ocean_current_direction_deg?: number;
  sst_c?: number;
  sea_state_code?: number;
  sea_state_description?: string;
  data_source: string;
}

export interface PFZZone {
  lat: number;
  lng: number;
  distance_km: number;
  chlorophyll_mgm3?: number;
  sst_c?: number;
  sst_gradient?: number;
  risk_level?: RiskLevel;
  score: number;
  reasoning: string;
}

export interface PFZReport {
  zones: PFZZone[];
  search_radius_km: number;
  data_source: string;
}

export interface RiskFactorScore {
  factor: string;
  score: number;
  weight: number;
  weighted_score: number;
  detail: string;
}

export interface RiskScore {
  final_score: number;
  risk_level: RiskLevel;
  risk_label: string;
  risk_emoji: string;
  risk_color: string;
  primary_hazard: string;
  primary_hazard_score: number;
  factor_scores: RiskFactorScore[];
  vessel_recommendation: string;
  data_source: string;
}

export interface RouteWaypoint {
  lat: number;
  lng: number;
  wave_risk?: number;
  weather_risk?: number;
  sea_state_risk?: number;
}

export interface RouteCandidate {
  route_id: string;
  name: string;
  waypoints: RouteWaypoint[];
  total_distance_km: number;
  safety_score: number;
  weather_score: number;
  sea_state_score: number;
  distance_score: number;
  fuel_score: number;
  overall_score: number;
  recommended: boolean;
  reasoning: string;
}

export interface RouteReport {
  routes: RouteCandidate[];
  recommended_route_id?: string;
}

export interface MapMarker {
  type: string;
  lat: number;
  lng: number;
  label: string;
  icon: string;
  score?: number;
  distance?: number;
  sst?: number;
}

export interface MapZone {
  type: string;
  center_lat: number;
  center_lng: number;
  radius_km: number;
  risk_level: string;
  risk_color: string;
  risk_score: number;
}

export interface MapRoute {
  route_id: string;
  name: string;
  recommended: boolean;
  waypoints: { lat: number; lng: number }[];
  overall_score: number;
  color: string;
}

export interface MapData {
  center: { lat: number; lng: number };
  zoom: number;
  markers: MapMarker[];
  zones: MapZone[];
  routes: MapRoute[];
}

export interface OrcaResponse {
  intent: Intent;
  language: Language;
  recommendation: string;
  explanation: string;
  risk_score?: RiskScore;
  weather_report?: WeatherReport;
  ocean_report?: OceanReport;
  pfz_report?: PFZReport;
  geospatial_report?: Record<string, unknown>;
  route_report?: RouteReport;
  agent_traces: AgentTrace[];
  map_data?: MapData;
  conversation_id: string;
  timestamp: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'orca';
  content: string;
  timestamp: string;
  response?: OrcaResponse;
  isLoading?: boolean;
}

export interface WSEvent {
  type: string;
  agent?: string;
  status?: AgentStatusType;
  message: string;
  data?: Record<string, unknown>;
  timestamp: string;
}

export interface Harbor {
  lat: number;
  lng: number;
  state: string;
  name: string;
}
