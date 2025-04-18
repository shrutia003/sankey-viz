import pandas as pd
from datetime import timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

features = pd.read_csv("Features1.csv", encoding="latin1")
reviews = pd.read_csv("AppReviews.csv", encoding='latin1')
labeled = pd.read_csv("Labeled_Reviews.csv", encoding='latin1')

features['Release Date'] = pd.to_datetime(features['Release Date'], errors='coerce')
reviews['Date'] = pd.to_datetime(reviews['Date'], errors='coerce')

merged = reviews.merge(features, left_on='MatchedFeatureID', right_on='Feature Id', how='left')
merged = merged[merged['ReviewText'].notna() & (merged['ReviewText'].str.strip() != "")]
merged['Within2Weeks'] = (merged['Date'] - merged['Release Date']).dt.days.between(0, 14)
merged['Review Period'] = merged['Date'].dt.to_period('Q').astype(str)

X_train = labeled['Review text']
y_train = labeled['Cluster']

tfidf = TfidfVectorizer(stop_words='english', max_features=200)
X_vec = tfidf.fit_transform(X_train)

clf = LogisticRegression(max_iter=1000)
clf.fit(X_vec, y_train)

X_reviews = tfidf.transform(merged['ReviewText'])
merged['Cluster'] = clf.predict(X_reviews)

all_time = merged.groupby(['Feature Title', 'Cluster']).size().reset_index(name='Value')
all_time['Filter'] = 'All Time'

by_quarter = merged.groupby(['Feature Title', 'Cluster', 'Review Period']).size().reset_index(name='Value')
by_quarter.rename(columns={'Review Period': 'Filter'}, inplace=True)

within_2wk = merged[merged['Within2Weeks']].groupby(['Feature Title', 'Cluster']).size().reset_index(name='Value')
within_2wk['Filter'] = 'Within 2 Weeks'

sankey_data = pd.concat([all_time, by_quarter, within_2wk], ignore_index=True)
sankey_data.to_csv("Preprocessed_Sankey_Data.csv", index=False)
merged.to_csv("Merged_Reviews_With_Features.csv", index=False)
print("Files created: Preprocessed_Sankey_Data.csv and Merged_Reviews_With_Features.csv")
