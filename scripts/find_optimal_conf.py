from ultralytics import YOLO

def main():
    model = YOLO('models/yolov11_infalsus_best.pt')
    print("=" * 60)
    print("  掃描不同信心度門檻 (Confidence Threshold) 下的精準度變化")
    print("=" * 60)
    best_f1 = 0
    best_conf = 0.4
    for conf in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
        metrics = model.val(data='data/data.yaml', device='cuda:0', conf=conf, workers=1, verbose=False)
        p = metrics.box.mp * 100
        r = metrics.box.mr * 100
        f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0
        map50 = metrics.box.map50 * 100
        print(f"Conf={conf:.2f} => Precision: {p:.2f}% | Recall: {r:.2f}% | F1: {f1:.2f}% | mAP50: {map50:.2f}%")
        if f1 > best_f1:
            best_f1 = f1
            best_conf = conf
    print(f"\n最佳平衡門檻: Conf = {best_conf:.2f} (最高 F1 = {best_f1:.2f}%)")

if __name__ == '__main__':
    main()
