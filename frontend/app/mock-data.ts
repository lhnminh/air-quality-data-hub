export type AirObservation = {
  source: string;
  collected_at: string;
  observed_at: string;
  city: string;
  state: string;
  country: string;
  longitude: number;
  latitude: number;
  aqi_us: number;
  main_pollutant: string;
};

export type WeatherObservation = {
  source: string;
  collected_at: string;
  observed_at: string;
  longitude: number;
  latitude: number;
  temperature_c: number;
  relative_humidity_percent: number;
  precipitation_mm: number;
  weather_code: number;
  wind_speed_kmh: number;
  wind_direction_degrees: number;
  wind_gusts_kmh: number;
};

export type ModeledAirQualityObservation = {
  source: string;
  collected_at: string;
  observed_at: string;
  longitude: number;
  latitude: number;
  us_aqi: number;
  pm2_5_ug_m3: number;
  pm10_ug_m3: number;
  nitrogen_dioxide_ug_m3: number;
  sulphur_dioxide_ug_m3: number;
  carbon_monoxide_ug_m3: number;
  ozone_ug_m3: number;
};

export type DistrictStatus = {
  district_name: string;
  weather_observed_at: string | null;
  wind_speed_kmh: number | null;
  wind_direction_degrees: number | null;
  wind_gusts_kmh?: number | null;
  temperature_c: number | null;
  relative_humidity_percent: number | null;
  precipitation_mm?: number | null;
  air_quality_observed_at: string | null;
  us_aqi: number | null;
  pm2_5_ug_m3: number | null;
  pm10_ug_m3: number | null;
  nitrogen_dioxide_ug_m3: number | null;
  sulphur_dioxide_ug_m3?: number | null;
  carbon_monoxide_ug_m3?: number | null;
  ozone_ug_m3: number | null;
};

// These rows keep the interface visible before the Python API is running.
// The yellow "Demo data" label always appears while these values are used.
export const mockObservations: AirObservation[] = [
  {
    source: "IQAir sample",
    collected_at: "2026-07-23T07:37:00Z",
    observed_at: "2026-07-23T07:00:00Z",
    city: "Hanoi",
    state: "Ha Noi",
    country: "Vietnam",
    longitude: 105.81881,
    latitude: 21.021938,
    aqi_us: 90,
    main_pollutant: "p2",
  },
  {
    source: "IQAir sample",
    collected_at: "2026-07-23T06:37:00Z",
    observed_at: "2026-07-23T06:00:00Z",
    city: "Hanoi",
    state: "Ha Noi",
    country: "Vietnam",
    longitude: 105.81881,
    latitude: 21.021938,
    aqi_us: 84,
    main_pollutant: "p2",
  },
  {
    source: "IQAir sample",
    collected_at: "2026-07-23T05:37:00Z",
    observed_at: "2026-07-23T05:00:00Z",
    city: "Hanoi",
    state: "Ha Noi",
    country: "Vietnam",
    longitude: 105.81881,
    latitude: 21.021938,
    aqi_us: 76,
    main_pollutant: "p2",
  },
  {
    source: "IQAir sample",
    collected_at: "2026-07-23T04:37:00Z",
    observed_at: "2026-07-23T04:00:00Z",
    city: "Hanoi",
    state: "Ha Noi",
    country: "Vietnam",
    longitude: 105.81881,
    latitude: 21.021938,
    aqi_us: 68,
    main_pollutant: "p2",
  },
  {
    source: "IQAir sample",
    collected_at: "2026-07-23T03:37:00Z",
    observed_at: "2026-07-23T03:00:00Z",
    city: "Hanoi",
    state: "Ha Noi",
    country: "Vietnam",
    longitude: 105.81881,
    latitude: 21.021938,
    aqi_us: 62,
    main_pollutant: "p2",
  },
];

// This keeps the dashboard useful before the weather collector has run.
export const mockWeatherObservations: WeatherObservation[] = [
  {
    source: "Open-Meteo sample",
    collected_at: "2026-07-23T07:37:00Z",
    observed_at: "2026-07-23T07:30:00Z",
    longitude: 105.834,
    latitude: 21.028,
    temperature_c: 30.4,
    relative_humidity_percent: 73,
    precipitation_mm: 0,
    weather_code: 2,
    wind_speed_kmh: 12.6,
    wind_direction_degrees: 118,
    wind_gusts_kmh: 19.8,
  },
];

export const mockModeledAirQualityObservations: ModeledAirQualityObservation[] = [
  {
    source: "Open-Meteo CAMS sample",
    collected_at: "2026-07-23T07:37:00Z",
    observed_at: "2026-07-23T07:30:00Z",
    longitude: 105.834,
    latitude: 21.028,
    us_aqi: 92,
    pm2_5_ug_m3: 32.5,
    pm10_ug_m3: 45.1,
    nitrogen_dioxide_ug_m3: 19.2,
    sulphur_dioxide_ug_m3: 4.0,
    carbon_monoxide_ug_m3: 530.4,
    ozone_ug_m3: 54.0,
  },
];

export const mockDistrictStatuses: DistrictStatus[] = [
  { district_name: "Tay Ho", weather_observed_at: "2026-07-23T07:30:00Z", wind_speed_kmh: 11.4, wind_direction_degrees: 110, temperature_c: 30.1, relative_humidity_percent: 72, air_quality_observed_at: "2026-07-23T07:30:00Z", us_aqi: 83, pm2_5_ug_m3: 28.1, pm10_ug_m3: 39.2, nitrogen_dioxide_ug_m3: 14.2, ozone_ug_m3: 58.0 },
  { district_name: "Long Bien", weather_observed_at: "2026-07-23T07:30:00Z", wind_speed_kmh: 12.7, wind_direction_degrees: 118, temperature_c: 30.5, relative_humidity_percent: 71, air_quality_observed_at: "2026-07-23T07:30:00Z", us_aqi: 94, pm2_5_ug_m3: 33.7, pm10_ug_m3: 46.3, nitrogen_dioxide_ug_m3: 18.9, ozone_ug_m3: 52.8 },
  { district_name: "Ba Dinh", weather_observed_at: "2026-07-23T07:30:00Z", wind_speed_kmh: 10.5, wind_direction_degrees: 114, temperature_c: 30.4, relative_humidity_percent: 73, air_quality_observed_at: "2026-07-23T07:30:00Z", us_aqi: 90, pm2_5_ug_m3: 31.8, pm10_ug_m3: 43.8, nitrogen_dioxide_ug_m3: 20.3, ozone_ug_m3: 53.2 },
  { district_name: "Cau Giay", weather_observed_at: "2026-07-23T07:30:00Z", wind_speed_kmh: 9.8, wind_direction_degrees: 108, temperature_c: 30.2, relative_humidity_percent: 74, air_quality_observed_at: "2026-07-23T07:30:00Z", us_aqi: 86, pm2_5_ug_m3: 29.6, pm10_ug_m3: 41.4, nitrogen_dioxide_ug_m3: 21.1, ozone_ug_m3: 54.9 },
  { district_name: "Hoan Kiem", weather_observed_at: "2026-07-23T07:30:00Z", wind_speed_kmh: 10.8, wind_direction_degrees: 116, temperature_c: 30.6, relative_humidity_percent: 73, air_quality_observed_at: "2026-07-23T07:30:00Z", us_aqi: 97, pm2_5_ug_m3: 35.4, pm10_ug_m3: 48.3, nitrogen_dioxide_ug_m3: 24.2, ozone_ug_m3: 51.6 },
  { district_name: "Dong Da", weather_observed_at: "2026-07-23T07:30:00Z", wind_speed_kmh: 9.9, wind_direction_degrees: 113, temperature_c: 30.5, relative_humidity_percent: 74, air_quality_observed_at: "2026-07-23T07:30:00Z", us_aqi: 95, pm2_5_ug_m3: 34.0, pm10_ug_m3: 46.9, nitrogen_dioxide_ug_m3: 23.7, ozone_ug_m3: 52.4 },
  { district_name: "Hai Ba Trung", weather_observed_at: "2026-07-23T07:30:00Z", wind_speed_kmh: 10.2, wind_direction_degrees: 120, temperature_c: 30.7, relative_humidity_percent: 72, air_quality_observed_at: "2026-07-23T07:30:00Z", us_aqi: 99, pm2_5_ug_m3: 36.1, pm10_ug_m3: 49.5, nitrogen_dioxide_ug_m3: 21.8, ozone_ug_m3: 50.7 },
  { district_name: "Thanh Xuan", weather_observed_at: "2026-07-23T07:30:00Z", wind_speed_kmh: 9.4, wind_direction_degrees: 111, temperature_c: 30.3, relative_humidity_percent: 75, air_quality_observed_at: "2026-07-23T07:30:00Z", us_aqi: 92, pm2_5_ug_m3: 32.9, pm10_ug_m3: 45.7, nitrogen_dioxide_ug_m3: 22.5, ozone_ug_m3: 53.1 },
];
