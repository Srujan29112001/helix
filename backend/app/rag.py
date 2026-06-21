"""Lightweight RAG over data-science documentation (Phase 5).

A curated corpus of pandas / scikit-learn / FLAML / SHAP recipes is embedded
with a local MiniLM model (ChromaDB's default, ONNX — no GPU) and stored in
ChromaDB. The Coder retrieves the most relevant snippets to ground its code,
cutting hallucinated APIs.

Falls back to a keyword match if ChromaDB/embeddings are unavailable, so the
pipeline never breaks.
"""

from __future__ import annotations

_DOCS: list[tuple[str, str]] = [
    ("pandas-missing", "Handle missing values: fill numeric columns with df.fillna(df.median(numeric_only=True)); fill categoricals with the mode df['c'].fillna(df['c'].mode()[0])."),
    ("pandas-encode", "Encode categorical features for tree models with label codes: df['c'] = df['c'].astype('category').cat.codes; or one-hot via pd.get_dummies(df, columns=cols)."),
    ("pandas-numeric", "Coerce a numeric column stored as text: pd.to_numeric(df['c'], errors='coerce'). Aggregate only numeric columns with df.mean(numeric_only=True) to avoid TypeErrors."),
    ("flaml-automl", "FLAML AutoML: from flaml import AutoML; m=AutoML(); m.fit(X_train, y_train, task='classification', time_budget=30, metric='roc_auc'); preds=m.predict(X_test)."),
    ("sklearn-split", "Train/test split: from sklearn.model_selection import train_test_split; X_tr,X_te,y_tr,y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)."),
    ("sklearn-metrics", "Classification metrics: accuracy_score, roc_auc_score(y, proba[:,1]), precision_score, recall_score, f1_score. Regression: r2_score, mean_squared_error, mean_absolute_error."),
    ("shap-explain", "Explain a tree model with SHAP: import shap; e=shap.TreeExplainer(model); vals=e.shap_values(X_sample); rank features by abs(vals).mean(0); sign by vals.mean(0)."),
    ("eda-basic", "Quick EDA: df.shape, df.describe(), df['target'].value_counts(normalize=True), and df.corr(numeric_only=True) to find correlations with the target."),
    # --- pandas wrangling ---
    ("pandas-dates", "Parse dates and extract parts: d = pd.to_datetime(df['col'], errors='coerce'); df['year']=d.dt.year; df['month']=d.dt.month; df['dow']=d.dt.dayofweek; df['is_weekend']=d.dt.dayofweek>=5."),
    ("pandas-merge", "Join two tables on a key: pd.merge(left, right, on='id', how='left'). Use how='inner'|'outer'|'left'. Check for duplicate keys with df['id'].duplicated().sum() first."),
    ("pandas-groupby", "Aggregate by a group: df.groupby('cat')['value'].agg(['mean','median','count']). For multiple columns: df.groupby('cat').agg({'a':'mean','b':'sum'})."),
    ("pandas-pivot", "Reshape long to wide: df.pivot_table(index='id', columns='cat', values='val', aggfunc='mean', fill_value=0)."),
    ("pandas-dedupe", "Remove duplicate rows: df = df.drop_duplicates(); count first with df.duplicated().sum(). Drop constant columns: df = df.loc[:, df.nunique() > 1]."),
    ("pandas-outliers-iqr", "Flag outliers with the IQR rule: q1,q3 = df['c'].quantile([.25,.75]); iqr=q3-q1; mask=(df['c']<q1-1.5*iqr)|(df['c']>q3+1.5*iqr). Cap with df['c'].clip(lower,upper)."),
    ("pandas-binning", "Bucket a numeric column: pd.qcut(df['c'], q=4) for equal-frequency bins, or pd.cut(df['c'], bins=[0,18,65,120]) for fixed edges."),
    ("pandas-fillna-mode", "Fill categorical missing values with the mode: df['c'] = df['c'].fillna(df['c'].mode()[0]). Numeric: df['c'].fillna(df['c'].median())."),
    ("pandas-dtypes", "Downcast for memory: df['c'] = pd.to_numeric(df['c'], downcast='float'). Convert to category for low-cardinality strings: df['c'] = df['c'].astype('category')."),
    ("pandas-skew", "Check skew with df['c'].skew(); for a right-skewed positive column use np.log1p(df['c']) to make it more symmetric before linear models."),
    # --- sklearn preprocessing & pipelines ---
    ("sklearn-scale", "Standardize numeric features: from sklearn.preprocessing import StandardScaler; X_scaled = StandardScaler().fit_transform(X). Needed for KNN, SVM, KMeans, PCA."),
    ("sklearn-onehot", "One-hot encode for linear models: from sklearn.preprocessing import OneHotEncoder; OneHotEncoder(handle_unknown='ignore', sparse_output=False).fit_transform(X[cats])."),
    ("sklearn-pipeline", "Bundle steps: from sklearn.pipeline import Pipeline; Pipeline([('scale', StandardScaler()), ('model', LogisticRegression())]).fit(X_train, y_train)."),
    ("sklearn-coltransform", "Different transforms per column: from sklearn.compose import ColumnTransformer; ColumnTransformer([('num', StandardScaler(), num_cols), ('cat', OneHotEncoder(), cat_cols)])."),
    ("sklearn-impute", "Impute with sklearn: from sklearn.impute import SimpleImputer; SimpleImputer(strategy='median').fit_transform(X). Use strategy='most_frequent' for categoricals."),
    ("sklearn-targetencode", "Target-encode a high-cardinality category: from sklearn.preprocessing import TargetEncoder; TargetEncoder().fit_transform(X[['cat']], y) (fit on train only to avoid leakage)."),
    # --- models ---
    ("model-logreg", "Interpretable baseline: from sklearn.linear_model import LogisticRegression; LogisticRegression(max_iter=300, class_weight='balanced').fit(X,y); coef_ gives feature effects."),
    ("model-rf", "Robust default: from sklearn.ensemble import RandomForestClassifier; RandomForestClassifier(n_estimators=200, random_state=42).fit(X,y); feature_importances_ ranks features."),
    ("model-gboost", "Strong tabular model: from sklearn.ensemble import HistGradientBoostingClassifier; handles missing values natively and trains fast on large data."),
    ("model-knn", "Distance-based: from sklearn.neighbors import KNeighborsClassifier; KNeighborsClassifier(n_neighbors=5). Always scale features first."),
    ("model-svm", "Margin classifier: from sklearn.svm import SVC; SVC(probability=True, class_weight='balanced'). Scale features; use a small subset on large data (slow)."),
    ("model-naivebayes", "Fast probabilistic baseline: from sklearn.naive_bayes import GaussianNB; good for high-dimensional or text-derived numeric features."),
    ("model-linear-reg", "Regularized regression: from sklearn.linear_model import Ridge, Lasso, ElasticNet; ElasticNet(alpha=0.1, l1_ratio=0.5) balances L1/L2; scale X first."),
    ("model-kmeans", "Cluster: from sklearn.cluster import KMeans; pick k by silhouette: silhouette_score(X, KMeans(k).fit_predict(X)); scale features first."),
    ("model-isoforest", "Anomaly detection: from sklearn.ensemble import IsolationForest; IsolationForest(contamination='auto', random_state=42); fit_predict gives -1 for anomalies; score_samples for scores."),
    ("model-dbscan", "Density clustering / outliers: from sklearn.cluster import DBSCAN; DBSCAN(eps=0.5, min_samples=5).fit_predict(X); label -1 = noise/outlier."),
    # --- metrics & evaluation ---
    ("metrics-report", "Per-class breakdown: from sklearn.metrics import classification_report, confusion_matrix; print(classification_report(y_test, preds)); confusion_matrix(y_test, preds)."),
    ("metrics-roc", "ROC + AUC (binary): from sklearn.metrics import roc_curve, roc_auc_score; fpr,tpr,_ = roc_curve(y, proba[:,1]); auc = roc_auc_score(y, proba[:,1])."),
    ("metrics-pr", "Precision-recall curve (imbalanced): from sklearn.metrics import precision_recall_curve, average_precision_score; prefer PR-AUC over ROC-AUC when positives are rare."),
    ("metrics-regression", "Regression metrics: from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error; rmse = mean_squared_error(y, pred, squared=False)."),
    ("metrics-calibration", "Are probabilities trustworthy? from sklearn.calibration import calibration_curve; frac_pos, mean_pred = calibration_curve(y, proba[:,1], n_bins=10)."),
    ("cv-kfold", "Honest scores: from sklearn.model_selection import cross_val_score, StratifiedKFold; cross_val_score(model, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=42), scoring='roc_auc')."),
    ("cv-learning-curve", "Diagnose under/overfitting: from sklearn.model_selection import learning_curve; sizes,train,val = learning_curve(model, X, y, train_sizes=np.linspace(.2,1,5), cv=3)."),
    ("eval-permutation", "Model-agnostic importance: from sklearn.inspection import permutation_importance; permutation_importance(model, X_test, y_test, n_repeats=5).importances_mean."),
    ("eval-pdp", "What-if / partial dependence: from sklearn.inspection import partial_dependence; or hold other features at the median and vary one across its range, then predict."),
    # --- FLAML AutoML ---
    ("flaml-regression", "FLAML regression: AutoML().fit(X, y, task='regression', time_budget=30, metric='r2'). It searches LightGBM/XGBoost/RF/ExtraTrees/linear automatically."),
    ("flaml-estimators", "Restrict/expand the FLAML search: fit(..., estimator_list=['lgbm','xgboost','rf','extra_tree','kneighbor','lrl1','lrl2']). Use ['lgbm','xgboost'] on very large data for speed."),
    ("flaml-best", "After fit: automl.best_estimator (name), automl.best_config (hyper-params), automl.model.estimator (the fitted sklearn model), automl.predict / predict_proba."),
    # --- SHAP ---
    ("shap-summary", "Global view: import shap; shap.summary_plot(shap_values, X) ranks features and shows direction. For trees use shap.TreeExplainer(model)."),
    ("shap-direction", "Feature effect direction: sign of shap_values.mean(0) tells whether a feature pushes the prediction up (+) or down (-); abs().mean(0) gives importance magnitude."),
    ("shap-fallback", "If SHAP fails (e.g. non-tree model), fall back to model.feature_importances_ or sklearn permutation_importance for a robust ranking."),
    # --- statistics ---
    ("stats-ttest", "Compare a numeric across two groups: from scipy.stats import ttest_ind; ttest_ind(a, b, equal_var=False) (Welch). Non-normal? use mannwhitneyu(a, b)."),
    ("stats-anova", "Numeric across >2 groups: from scipy.stats import f_oneway; f_oneway(g1, g2, g3). Non-normal? use kruskal(g1, g2, g3)."),
    ("stats-chi2", "Two categoricals: from scipy.stats import chi2_contingency; chi2, p, dof, _ = chi2_contingency(pd.crosstab(a, b)). Effect size = Cramer's V."),
    ("stats-corr", "Correlation with significance: from scipy.stats import pearsonr, spearmanr; r, p = pearsonr(x, y). Spearman is rank-based (monotonic, robust to outliers)."),
    ("stats-normality", "Test normality: from scipy.stats import shapiro; stat, p = shapiro(x[:5000]). p<0.05 means non-normal -> prefer non-parametric tests."),
    ("stats-effect-size", "Beyond p-values: Cohen's d = (mean1-mean2)/pooled_std for means; Cramer's V = sqrt(chi2/(n*(min(r,c)-1))) for categoricals."),
    ("stats-ci", "Confidence interval for a mean: from scipy.stats import t; mean +/- t.ppf(.975, n-1) * (std/sqrt(n))."),
    # --- imbalanced & feature engineering ---
    ("imbalanced-smote", "Oversample the minority class (train only): from imblearn.over_sampling import SMOTE; X_res, y_res = SMOTE(random_state=42).fit_resample(X_train, y_train). Never resample the test set."),
    ("imbalanced-weights", "Cheaper alternative to SMOTE: pass class_weight='balanced' to the model, or compute sample_weight from sklearn.utils.class_weight.compute_sample_weight."),
    ("fe-interactions", "Create interaction features: df['a_x_b'] = df['a'] * df['b']; or sklearn PolynomialFeatures(degree=2, interaction_only=True) for all pairs."),
    ("fe-log", "Tame skew: df['log_x'] = np.log1p(df['x']) for positive right-skewed columns; helps linear models and stabilizes variance."),
    # --- time series ---
    ("ts-decompose", "Split trend/seasonal/residual: from statsmodels.tsa.seasonal import seasonal_decompose; seasonal_decompose(series, period=12, model='additive')."),
    ("ts-ets", "Forecast with Holt-Winters: from statsmodels.tsa.holtwinters import ExponentialSmoothing; ExponentialSmoothing(y, trend='add', seasonal='add', seasonal_periods=12).fit().forecast(12)."),
    ("ts-arima", "ARIMA forecast: from statsmodels.tsa.arima.model import ARIMA; ARIMA(y, order=(1,1,1)).fit().forecast(steps=12). Order = (AR, differencing, MA)."),
    # --- NLP ---
    ("nlp-tfidf", "Vectorize text: from sklearn.feature_extraction.text import TfidfVectorizer; X = TfidfVectorizer(max_features=500, stop_words='english').fit_transform(texts)."),
    ("nlp-lda", "Topic modelling: from sklearn.decomposition import LatentDirichletAllocation; fit on a CountVectorizer matrix; top words per topic = components_.argsort()."),
    ("nlp-sentiment", "Quick sentiment: score each text by counting words from a positive/negative lexicon, or use a pretrained model (VADER/transformers) for nuance."),
    # --- dimensionality reduction & survival ---
    ("dimred-pca", "Compress features: from sklearn.decomposition import PCA; p = PCA(n_components=2).fit(StandardScaler().fit_transform(X)); p.explained_variance_ratio_ shows info kept."),
    ("dimred-tsne", "Visualize high-dim data in 2D: from sklearn.manifold import TSNE; TSNE(n_components=2, perplexity=30).fit_transform(X). Good for clusters, not for modelling."),
    ("survival-km", "Kaplan-Meier survival curve: from lifelines import KaplanMeierFitter; KaplanMeierFitter().fit(durations, event_observed=events).survival_function_."),
    ("survival-cox", "Cox proportional hazards: from lifelines import CoxPHFitter; CoxPHFitter().fit(df, duration_col='T', event_col='E'); hazard_ratios_ >1 = higher risk."),
]

_collection = None
_failed = False


def _get_collection():
    global _collection, _failed
    if _collection is not None or _failed:
        return _collection
    try:
        import chromadb

        client = chromadb.Client()
        col = client.get_or_create_collection("ds_docs")
        if col.count() == 0:
            col.add(ids=[d[0] for d in _DOCS], documents=[d[1] for d in _DOCS])
        _collection = col
    except Exception:
        _failed = True
        _collection = None
    return _collection


def _keyword_fallback(query: str, k: int) -> list[str]:
    q = set(query.lower().split())
    scored = sorted(_DOCS, key=lambda d: -len(q & set(d[1].lower().split())))
    return [d[1] for d in scored[:k]]


def retrieve(query: str, k: int = 2) -> list[str]:
    """Return the k most relevant documentation snippets for a query."""
    col = _get_collection()
    if col is not None:
        try:
            res = col.query(query_texts=[query], n_results=min(k, len(_DOCS)))
            docs = res.get("documents") if res else None
            if docs and docs[0]:
                return docs[0]
        except Exception:
            pass
    return _keyword_fallback(query, k)
