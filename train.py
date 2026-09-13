import numpy as np, joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss, accuracy_score

d = np.load("data.npz", allow_pickle=True)
X, Y, G, names = d["X"], d["Y"], d["G"], list(d["names"])

# split by GAME id -- rows from one game must never straddle the split
games = np.unique(G)
cut = int(len(games)*0.8)
train_g, test_g = set(games[:cut]), set(games[cut:])
tr = np.array([g in train_g for g in G]); te = ~tr
print(f"train {tr.sum():,} rows / test {te.sum():,} rows")

clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08,
                                     max_leaf_nodes=31, random_state=0)
clf.fit(X[tr], Y[tr])
prob = clf.predict_proba(X[te])[:,1]

print(f"\nAUC        {roc_auc_score(Y[te], prob):.4f}")
print(f"accuracy   {accuracy_score(Y[te], prob>0.5):.4f}  (base {max(Y[te].mean(),1-Y[te].mean()):.4f})")
print(f"Brier      {brier_score_loss(Y[te], prob):.4f}")

turn_i = names.index("turn")
print("\nAUC by game stage:")
for lo, hi in [(0,20),(20,40),(40,60),(60,90),(90,300)]:
    m = (X[te][:,turn_i]>=lo)&(X[te][:,turn_i]<hi)
    if m.sum()>500 and len(np.unique(Y[te][m]))>1:
        print(f"  turns {lo:3}-{hi:3}: AUC {roc_auc_score(Y[te][m], prob[m]):.3f}  ({m.sum():,} rows)")

# calibration
print("\ncalibration (predicted -> actual win rate):")
for lo in np.arange(0,1,0.1):
    m=(prob>=lo)&(prob<lo+0.1)
    if m.sum()>200: print(f"  {lo:.1f}-{lo+0.1:.1f}: {Y[te][m].mean():.3f}  (n={m.sum():,})")

from sklearn.inspection import permutation_importance
idx = np.random.default_rng(0).choice(np.where(te)[0], 15000, replace=False)
r = permutation_importance(clf, X[idx], Y[idx], n_repeats=3, random_state=0, scoring="roc_auc")
print("\ntop features:")
for i in r.importances_mean.argsort()[::-1][:10]:
    print(f"  {names[i]:24} {r.importances_mean[i]:.4f}")

joblib.dump({"model": clf, "names": names}, "model.pkl")
print("\nsaved model.pkl")