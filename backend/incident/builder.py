"""
Incident context builder.

Groups Phase 2 anomaly events into deterministic incidents, attaches bounded
context, and returns stable, machine-consumable incident objects.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

from src.anomaly.schema import AnomalyEvent, FeatureAnomaly
from src.data.schema import LogEntry

from .config import IncidentConfig
from .schema import Incident, LogPattern, MetricsSummary, OperationalEvent


class IncidentBuilder:
    """
    Deterministic incident builder.

    Grouping rules:
    - Group by service.
    - Group by time proximity (max_gap_seconds).
    - If require_feature_family_overlap is True, only group events that share
      at least one feature family.

    Assumptions:
    - Phase 2 AnomalyEvent provides window_start only. Incident end_time is
      computed using window_size_seconds.
    """

    def __init__(self, config: Optional[IncidentConfig] = None) -> None:
        self.config = config or IncidentConfig()

    def build_incidents(
        self,
        anomaly_events: Iterable[AnomalyEvent],
        logs_by_service: Optional[Dict[str, List[LogEntry]]] = None,
        operational_events: Optional[List[OperationalEvent]] = None,
    ) -> List[Incident]:
        """
        Build incidents from anomaly events.

        Args:
            anomaly_events: Iterable of AnomalyEvent objects.
            logs_by_service: Optional mapping of service -> LogEntry list.
            operational_events: Optional list of OperationalEvent objects.

        Returns:
            List of Incident objects, sorted by service and start_time.
        """
        events = sorted(
            anomaly_events,
            key=lambda e: (e.service, e.window_start, e.detected_at),
        )

        incidents: List[Incident] = []
        current_group: List[AnomalyEvent] = []

        def flush_group() -> None:
            if not current_group:
                return
            incident = self._build_incident(current_group, logs_by_service, operational_events)
            incidents.append(incident)
            current_group.clear()

        for event in events:
            if not current_group:
                current_group.append(event)
                continue

            if self._should_group(current_group, event):
                current_group.append(event)
            else:
                flush_group()
                current_group.append(event)

        flush_group()

        incidents.sort(key=lambda i: (i.service, i.start_time))
        return incidents

    def _should_group(self, group: List[AnomalyEvent], event: AnomalyEvent) -> bool:
        last_event = group[-1]
        gap = (event.window_start - last_event.window_start).total_seconds()
        if gap > self.config.max_gap_seconds:
            return False

        if not self.config.require_feature_family_overlap:
            return True

        group_families = self._event_family_set(group)
        event_families = self._event_family_set([event])
        return len(group_families & event_families) > 0

    def _event_family_set(self, events: List[AnomalyEvent]) -> set:
        families = set()
        for event in events:
            for anomaly in event.anomalies:
                family = self.config.feature_families.get(anomaly.feature, "other")
                families.add(family)
        return families

    def _build_incident(
        self,
        events: List[AnomalyEvent],
        logs_by_service: Optional[Dict[str, List[LogEntry]]],
        operational_events: Optional[List[OperationalEvent]],
    ) -> Incident:
        service = events[0].service
        start_time, end_time = self._incident_time_bounds(events)
        anomalies_sorted = sorted(events, key=lambda e: (e.window_start, e.detected_at))

        metrics_summary = self._metrics_summary(events)
        log_patterns = self._derive_log_patterns(service, start_time, end_time, logs_by_service)
        op_context = self._derive_operational_context(start_time, end_time, operational_events)

        return Incident(
            service=service,
            start_time=start_time,
            end_time=end_time,
            anomalies=anomalies_sorted,
            metrics_summary=metrics_summary,
            log_patterns=log_patterns,
            operational_context=op_context,
        )

    def _incident_time_bounds(self, events: List[AnomalyEvent]) -> Tuple[datetime, datetime]:
        start = min(e.window_start for e in events)
        end = max(e.window_start for e in events)
        end = end + timedelta(seconds=self.config.window_size_seconds)
        return start, end

    def _metrics_summary(self, events: List[AnomalyEvent]) -> MetricsSummary:
        severities: Dict[str, int] = {}
        features = set()
        max_score = 0.0

        for event in events:
            max_score = max(max_score, event.score)
            for anomaly in event.anomalies:
                features.add(anomaly.feature)
                key = anomaly.severity
                severities[key] = severities.get(key, 0) + 1

        return MetricsSummary(
            anomaly_count=len(events),
            feature_count=len(features) if features else 1,
            max_score=max_score,
            severity_counts=severities,
        )

    def _derive_log_patterns(
        self,
        service: str,
        start_time: datetime,
        end_time: datetime,
        logs_by_service: Optional[Dict[str, List[LogEntry]]],
    ) -> List[LogPattern]:
        if not logs_by_service or service not in logs_by_service:
            return []

        context_start = start_time - timedelta(seconds=self.config.context_window_seconds)
        context_end = end_time + timedelta(seconds=self.config.context_window_seconds)

        patterns: Dict[str, LogPattern] = {}
        for log in logs_by_service[service]:
            if log.timestamp < context_start or log.timestamp > context_end:
                continue
            key = str(log.metadata.get("message_hash") or log.message)
            if key not in patterns:
                patterns[key] = LogPattern(key=key, count=1, sample_message=log.message)
            else:
                patterns[key].count += 1

        pattern_list = sorted(patterns.values(), key=lambda p: p.count, reverse=True)
        return pattern_list[: self.config.max_log_patterns]

    def _derive_operational_context(
        self,
        start_time: datetime,
        end_time: datetime,
        operational_events: Optional[List[OperationalEvent]],
    ) -> List[OperationalEvent]:
        if not operational_events:
            return []

        context_start = start_time - timedelta(seconds=self.config.context_window_seconds)
        context_end = end_time + timedelta(seconds=self.config.context_window_seconds)

        filtered = [
            e
            for e in operational_events
            if context_start <= e.timestamp <= context_end
        ]
        filtered.sort(key=lambda e: e.timestamp)
        return filtered[: self.config.max_operational_events]

