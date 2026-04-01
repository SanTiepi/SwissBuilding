/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under BuildingDetail (Building Home).
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useAuth } from '@/hooks/useAuth';
import ExtractionReviewComponent from '@/components/extractions/ExtractionReview';

export default function ExtractionReviewPage() {
  useAuth();
  return <ExtractionReviewComponent />;
}
