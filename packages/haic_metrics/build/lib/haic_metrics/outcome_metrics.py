
from typing import Dict, List, Any




class Metrics:
    """
    Flexible outcome metrics with alias-aware field access and robust TP/FP/FN/TN derivation.
    Configure positive/negative vocab as needed in _CFG below.
    """

    # ---- Global config (edit to your domain) ----
    _CFG = {
        "aliases": {
            # labels / outcomes
            "result_label": ["ai_detection_results", "result", "outcome_label"],  # expects: true_positive, false_positive, true_negative, false_negative
            "prediction":   ["prediction", "predicted", "pred_label", "ai_label", "ai_decision", "ai_suggestion"],
            "ground_truth": ["ground_truth", "true_label", "label", "human_label", "human_decision", "op_decision"],
            "outcome_bool": ["correct", "is_correct", "agreement"],  # boolean where present

            # times / resources
            "response_time_s": ["response_time", "time_to_response", "resolution_time", "duration_s", "handle_time_s"],
            "latency_ms":      ["latency_ms", "inference_ms", "latency"],
            "time_with_ai":    ["time_with_ai"],
            "time_without_ai": ["time_without_ai"],
            "correction_time": ["correction_time", "time_spent_correcting"],
            "time_spent":      ["time_spent", "learning_time", "total_time"],
            "performance_improvement": ["performance_improvement", "learning_gain"],
            "resources_used":  ["resources_used", "cpu_used", "gpu_used", "mem_used"],
            "total_resources": ["total_resources", "cpu_total", "gpu_total", "mem_total"],

            # counts / flags
            "reached_target": ["reached_target", "meets_target", "target_reached"],
            "correction_effectiveness": ["correction_effectiveness"],
            "errors_before": ["errors_before"],
            "errors_after":  ["errors_after"],
            "pre_retention_performance":  ["pre_retention_performance"],
            "post_retention_performance": ["post_retention_performance"],
            "pre_feedback_performance":   ["pre_feedback_performance"],
            "post_feedback_performance":  ["post_feedback_performance"],
            "pre_adaptation_performance": ["pre_adaptation_performance"],
            "post_adaptation_performance":["post_adaptation_performance"],
            "pre_correction_performance": ["pre_correction_performance"],
            "post_correction_performance":["post_correction_performance"],

            # trust / confidence / safety
            "confidence_level":    ["confidence_level", "confidence"],
            "result_correct_str":  ["result", "outcome"],  # expects "correct"/"incorrect"
            "trust_rating":        ["trust_rating"],
            "trust_scale_maximum": ["trust_scale_maximum"],
            "safety_incidents":    ["safety_incidents"],

            # reliability
            "uptime":      ["uptime"],
            "total_time":  ["total_time"],

            # robustness / generalization
            "performance_adversarial":   ["performance_adversarial"],
            "performance_normal":        ["performance_normal"],
            "performance_across_domains":["performance_across_domains"],
            "baseline_performance":      ["baseline_performance"],
        },

        # What counts as positive vs negative when inferring from labels/decisions
        "positive_vocab": {
            "positive","pos","yes","1","true","flagged","rejected","anomaly","error","issue","defect","unsafe","invalid"
        },
        "negative_vocab": {
            "negative","neg","no","0","false","accepted","ok","valid","secure","correct","safe"
        },

        # Strings that mean "correct outcome"
        "correct_token": {"correct", "true", "1", True},
    }

    # ---------- helpers ----------
    @staticmethod
    def _pick(item, keys, default=None):
        for k in keys:
            if k in item and item[k] not in (None, "", [], {}):
                return item[k]
        return default

    @classmethod
    def _get(cls, item, logical_key, default=None):
        return cls._pick(item, cls._CFG["aliases"][logical_key], default)

    @staticmethod
    def _to_float(x, default=0.0):
        try:
            if isinstance(x, bool):
                return 1.0 if x else 0.0
            return float(x)
        except Exception:
            return default

    @classmethod
    def _response_seconds(cls, item):
        """Prefer seconds fields; fall back to latency_ms converted to seconds."""
        s = cls._get(item, "response_time_s")
        if s is not None:
            return cls._to_float(s, 0.0)
        ms = cls._get(item, "latency_ms")
        if ms is not None:
            return cls._to_float(ms, 0.0) / 1000.0
        return 0.0

    @classmethod
    def _is_positive(cls, label):
        if label is None:
            return None
        s = str(label).strip().lower()
        if s in cls._CFG["positive_vocab"]:
            return True
        if s in cls._CFG["negative_vocab"]:
            return False
        # numeric / boolean fallbacks
        if s in {"1", "true", "t", "yes"}:
            return True
        if s in {"0", "false", "f", "no"}:
            return False
        return None  # unknown

    @classmethod
    def _derive_confusion_from_result_label(cls, val):
        """
        If item has a single label like 'true_positive', return a one-hot dict.
        """
        if not val:
            return None
        s = str(val).strip().lower()
        if s in {"true_positive","tp"}:  return {"tp":1,"fp":0,"tn":0,"fn":0}
        if s in {"false_positive","fp"}: return {"tp":0,"fp":1,"tn":0,"fn":0}
        if s in {"true_negative","tn"}:  return {"tp":0,"fp":0,"tn":1,"fn":0}
        if s in {"false_negative","fn"}: return {"tp":0,"fp":0,"tn":0,"fn":1}
        return None

    @classmethod
    def _derive_confusion_from_pair(cls, pred, gt):
        """
        Try to infer TP/FP/TN/FN from prediction/ground-truth labels using vocab.
        Returns dict or None if unknown.
        """
        p = cls._is_positive(pred)
        g = cls._is_positive(gt)
        if p is None or g is None:
            return None
        if p and g:   return {"tp":1,"fp":0,"tn":0,"fn":0}
        if p and not g: return {"tp":0,"fp":1,"tn":0,"fn":0}
        if not p and not g: return {"tp":0,"fp":0,"tn":1,"fn":0}
        if not p and g:   return {"tp":0,"fp":0,"tn":0,"fn":1}

    @classmethod
    def _derive_confusion(cls, item):
        """
        Order:
          1) explicit result_label true_positive/...
          2) (prediction, ground_truth)
          3) (ai_decision, op_decision) routed via aliases above
        """
        lbl = cls._get(item, "result_label")
        c = cls._derive_confusion_from_result_label(lbl)
        if c: return c

        pred = cls._get(item, "prediction")
        gt   = cls._get(item, "ground_truth")
        c = cls._derive_confusion_from_pair(pred, gt)
        if c: return c

        # Some logs only have ai_decision/op_decision under the same aliases
        ai_dec = cls._get(item, "prediction")
        op_dec = cls._get(item, "ground_truth")
        c = cls._derive_confusion_from_pair(ai_dec, op_dec)
        return c or {"tp":0,"fp":0,"tn":0,"fn":0}

    @classmethod
    def _bool_correct(cls, item):
        # Prefer explicit boolean
        b = cls._get(item, "outcome_bool")
        if b is not None:
            return bool(b)
        # Accept strings like "correct"/"incorrect"
        s = cls._get(item, "result_correct_str")
        if s is not None:
            return str(s).strip().lower() in cls._CFG["correct_token"]
        # Fallback from confusion one-hot if available
        conf = cls._derive_confusion(item)
        # correct if TP or TN
        return (conf.get("tp",0) + conf.get("tn",0)) > 0

    # ---------- Effectiveness ----------
    class Effectiveness:
        @staticmethod
        def calculate_prediction_accuracy(interaction_data):
            # accuracy = (TP + TN) / N
            tp = tn = 0
            n = 0
            for it in interaction_data:
                conf = Metrics._derive_confusion(it)
                tp += conf.get("tp", 0); tn += conf.get("tn", 0)
                n += sum(conf.values()) or 1  # assume 1 when not explicit
            return (tp + tn) / n if n > 0 else 0.0

        @staticmethod
        def calculate_precision(interaction_data):
            tp = fp = 0
            for it in interaction_data:
                conf = Metrics._derive_confusion(it)
                tp += conf.get("tp", 0); fp += conf.get("fp", 0)
            return tp / (tp + fp) if (tp + fp) > 0 else 0.0

        @staticmethod
        def calculate_recall(interaction_data):
            tp = fn = 0
            for it in interaction_data:
                conf = Metrics._derive_confusion(it)
                tp += conf.get("tp", 0); fn += conf.get("fn", 0)
            return tp / (tp + fn) if (tp + fn) > 0 else 0.0

        @staticmethod
        def calculate_overall_system_accuracy(interaction_data):
            correct = 0; total = 0
            for it in interaction_data:
                correct += 1 if Metrics._bool_correct(it) else 0
                total += 1
            return (correct / total) * 100 if total > 0 else 0.0

        @staticmethod
        def calculate_model_improvement_rate(interaction_data):
            t  = sum(Metrics._to_float(Metrics._get(it, "post_adaptation_performance"), 0.0) for it in interaction_data)
            t1 = sum(Metrics._to_float(Metrics._get(it, "pre_adaptation_performance"), 0.0) for it in interaction_data)
            dt = len(interaction_data) or 0
            # If you have explicit time deltas, alias them to "time_interval" and use that instead:
            explicit_dt = sum(Metrics._to_float(it.get("time_interval", 0.0), 0.0) for it in interaction_data)
            denom = explicit_dt if explicit_dt > 0 else (dt if dt > 0 else 1.0)
            return (t - t1) / denom

    # ---------- Efficiency ----------
    class Efficiency:
        @staticmethod
        def calculate_response_time(interaction_data):
            times = [Metrics._response_seconds(it) for it in interaction_data]
            return sum(times) / len(times) if times else 0.0

        @staticmethod
        def calculate_teaching_efficiency(interaction_data):
            gain = sum(Metrics._to_float(Metrics._get(it, "performance_improvement"), 0.0) for it in interaction_data)
            spent = sum(Metrics._to_float(Metrics._get(it, "time_spent"), 0.0) for it in interaction_data)
            return (gain / spent) if spent > 0 else 0.0

        @staticmethod
        def calculate_query_efficiency(interaction_data):
            total = len(interaction_data)
            hits = sum(1 for it in interaction_data if bool(Metrics._get(it, "reached_target", False)))
            return (total / hits) if hits > 0 else 0.0

        @staticmethod
        def calculate_resource_utilization(interaction_data):
            used = sum(Metrics._to_float(Metrics._get(it, "resources_used"), 0.0) for it in interaction_data)
            tot  = sum(Metrics._to_float(Metrics._get(it, "total_resources"), 0.0) for it in interaction_data)
            return (used / tot) * 100.0 if tot > 0 else 0.0

        @staticmethod
        def calculate_task_completion_time(interaction_data):
            t_wo = sum(Metrics._to_float(Metrics._get(it, "time_without_ai"), 0.0) for it in interaction_data)
            t_w  = sum(Metrics._to_float(Metrics._get(it, "time_with_ai"), 0.0) for it in interaction_data)
            return t_wo - t_w

        @staticmethod
        def calculate_correction_efficiency(interaction_data):
            eff = sum(Metrics._to_float(Metrics._get(it, "correction_effectiveness"), 0.0) for it in interaction_data)
            time = sum(Metrics._to_float(Metrics._get(it, "correction_time"), 0.0) for it in interaction_data)
            return (eff / time) if time > 0 else 0.0

        @staticmethod
        def calculate_error_reduction_rate(interaction_data):
            before = sum(Metrics._to_float(Metrics._get(it, "errors_before"), 0.0) for it in interaction_data)
            after  = sum(Metrics._to_float(Metrics._get(it, "errors_after"), 0.0) for it in interaction_data)
            return ((before - after) / before) * 100.0 if before > 0 else 0.0

        @staticmethod
        def calculate_knowledge_retention(interaction_data):
            pre  = sum(Metrics._to_float(Metrics._get(it, "pre_retention_performance"), 0.0) for it in interaction_data)
            post = sum(Metrics._to_float(Metrics._get(it, "post_retention_performance"), 0.0) for it in interaction_data)
            return (post / pre) * 100.0 if pre > 0 else 0.0

    # ---------- Adaptability & Learning ----------
    class AdaptabilityAndLearning:
        @staticmethod
        def calculate_feedback_impact(interaction_data):
            pre  = sum(Metrics._to_float(Metrics._get(it, "pre_feedback_performance"), 0.0) for it in interaction_data)
            post = sum(Metrics._to_float(Metrics._get(it, "post_feedback_performance"), 0.0) for it in interaction_data)
            return post - pre

        @staticmethod
        def calculate_adaptability_score(interaction_data):
            pre  = sum(Metrics._to_float(Metrics._get(it, "pre_adaptation_performance"), 0.0) for it in interaction_data)
            post = sum(Metrics._to_float(Metrics._get(it, "post_adaptation_performance"), 0.0) for it in interaction_data)
            return post - pre

        @staticmethod
        def calculate_impact_of_corrections(interaction_data):
            pre  = sum(Metrics._to_float(Metrics._get(it, "pre_correction_performance"), 0.0) for it in interaction_data)
            post = sum(Metrics._to_float(Metrics._get(it, "post_correction_performance"), 0.0) for it in interaction_data)
            return post - pre

        @staticmethod
        def calculate_learning_efficiency(interaction_data):
            gains = sum(Metrics._to_float(Metrics._get(it, "performance_improvement"), 0.0) for it in interaction_data)
            time  = sum(Metrics._to_float(Metrics._get(it, "time_spent"), 0.0) for it in interaction_data)
            return gains / time if time > 0 else 0.0

        @staticmethod
        def calculate_objective_fulfillment_rate(interaction_data):
            achieved = sum(1 for it in interaction_data if str(Metrics._get(it, "ground_truth", "")).strip().lower() in {"achieved","done","met"} or str(it.get("objective_status","")).lower()=="achieved")
            total = len(interaction_data)
            return achieved / total if total > 0 else 0.0

    # ---------- Collaboration & Interaction ----------
    class CollaborationAndInteraction:
        @staticmethod
        def calculate_human_ai_agreement_rate(interaction_data):
            agree = 0; total = 0
            for it in interaction_data:
                h = Metrics._get(it, "ground_truth")
                a = Metrics._get(it, "prediction")
                if h is None and a is None:
                    continue
                total += 1
                agree += 1 if str(h).strip().lower() == str(a).strip().lower() else 0
            return agree / total if total > 0 else 0.0

        @staticmethod
        def calculate_ai_assistance_rate(interaction_data):
            assisted = sum(1 for it in interaction_data if bool(it.get("ai_assisted") or it.get("assisted") or it.get("ai_help")))
            total = len(interaction_data)
            return assisted / total if total > 0 else 0.0

        @staticmethod
        def calculate_decision_effectiveness(interaction_data):
            succ = sum(1 for it in interaction_data if str(it.get("decision_outcome","")).strip().lower() in {"successful","success","ok"})
            total = len(interaction_data)
            return (succ / total) * 100.0 if total > 0 else 0.0

        @staticmethod
        def calculate_time_to_resolution(interaction_data):
            times = [Metrics._response_seconds(it) for it in interaction_data]
            return sum(times) / len(times) if times else 0.0

        @staticmethod
        def calculate_human_effort_saved(interaction_data):
            w = sum(Metrics._to_float(Metrics._get(it, "time_without_ai"), 0.0) for it in interaction_data)
            a = sum(Metrics._to_float(Metrics._get(it, "time_with_ai"), 0.0) for it in interaction_data)
            return w - a

    # ---------- Trust & Safety ----------
    class TrustAndSafety:
        @staticmethod
        def calculate_confidence(interaction_data):
            high = [it for it in interaction_data if Metrics._to_float(Metrics._get(it, "confidence_level"), 0.0) >= 0.9]
            good = [it for it in high if str(Metrics._get(it, "result_correct_str","")).strip().lower() in {"correct","true"} or Metrics._bool_correct(it)]
            return (len(good) / len(high)) * 100.0 if high else 0.0

        @staticmethod
        def calculate_trust_score(interaction_data):
            ratings = sum(Metrics._to_float(Metrics._get(it, "trust_rating"), 0.0) for it in interaction_data)
            scale   = sum(Metrics._to_float(Metrics._get(it, "trust_scale_maximum"), 0.0) for it in interaction_data)
            return (ratings / scale) * 100.0 if scale > 0 else 0.0

        @staticmethod
        def calculate_safety_incidents(interaction_data):
            return sum(Metrics._to_float(Metrics._get(it, "safety_incidents"), 0.0) for it in interaction_data)

        @staticmethod
        def calculate_system_reliability(interaction_data):
            up  = sum(Metrics._to_float(Metrics._get(it, "uptime"), 0.0) for it in interaction_data)
            tot = sum(Metrics._to_float(Metrics._get(it, "total_time"), 0.0) for it in interaction_data)
            return (up / tot) * 100.0 if tot > 0 else 0.0

    # ---------- Robustness & Generalization ----------
    class RobustnessAndGeneralization:
        @staticmethod
        def calculate_adversarial_robustness(interaction_data):
            adv = sum(Metrics._to_float(Metrics._get(it, "performance_adversarial"), 0.0) for it in interaction_data)
            nor = sum(Metrics._to_float(Metrics._get(it, "performance_normal"), 0.0) for it in interaction_data)
            return adv / nor if nor > 0 else 0.0

        @staticmethod
        def calculate_domain_generalization(interaction_data):
            diff = sum(Metrics._to_float(Metrics._get(it, "performance_across_domains"), 0.0) for it in interaction_data)
            base = sum(Metrics._to_float(Metrics._get(it, "baseline_performance"), 0.0) for it in interaction_data)
            return diff / base if base > 0 else 0.0

    @staticmethod
    def get_available_metrics():
        return {
            "Performance": [
                "Prediction Accuracy",
                "Precision",
                "Recall",
                "Overall System Accuracy",
                "Model Improvement Rate",
            ],
            "Efficiency": [
                "Response Time",
                "Teaching Efficiency",
                "Query Efficiency",
                "Resource Utilization",
                "Task Completion Time",
                "Correction Efficiency",
                "Error Reduction Rate",
                "Knowledge Retention",
            ],
            "Adaptability and Learning": [
                "Feedback Impact",
                "Adaptability Score",
                "Impact of Corrections",
                "Learning Efficiency",
                "Objective Fulfillment Rate",
            ],
            "Collaboration and Interaction": [
                "Human-AI Agreement Rate",
                "AI Assistance Rate",
                "Decision Effectiveness",
                "Time to Resolution",
                "Human Effort Saved",
            ],
            "Trust and Safety": [
                "Confidence",
                "Trust Score",
                "Safety Incidents",
                "System Reliability",
            ],
            "Robustness and Generalization": [
                "Adversarial Robustness",
                "Domain Generalization",
            ],
        }


def compute_outcome_metrics(
    decisions: List[Dict[str, Any]],
    *,
    profile: str = "core_outcomes",
) -> Dict[str, float]:
    """
    Outcome/quality catalogue (opt-in).
    'core_outcomes' focuses on generic, commonly-available outcome measures.
    """
    if profile != "core_outcomes":
        raise ValueError(f"Unknown profile: {profile}")

    return {
        "outcome_prediction_accuracy": float(Metrics.Effectiveness.calculate_prediction_accuracy(decisions)),
        "outcome_precision": float(Metrics.Effectiveness.calculate_precision(decisions)),
        "outcome_recall": float(Metrics.Effectiveness.calculate_recall(decisions)),
        "outcome_human_ai_agreement_rate": float(Metrics.CollaborationAndInteraction.calculate_human_ai_agreement_rate(decisions)),
        "outcome_trust_score": float(Metrics.TrustAndSafety.calculate_trust_score(decisions)),
    }