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
