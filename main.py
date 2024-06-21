from concurrent import futures
import grpc
import numpy as np

import recommendation_pb2
import recommendation_pb2_grpc
import pandas as pd

import logging


class RecommendationService(recommendation_pb2_grpc.RecommendationServiceServicer):
    def __init__(self):
        self.user_item_matrix, self.item_similarity_df, self.tfidf_matrix, self.indices, self.cosine_sim = self.get_user_item_matrix_and_item_similarity()
        logging.basicConfig(level=logging.INFO)

    def get_user_item_matrix_and_item_similarity(self):
        logging.info('data loading...')
        user_item_matrix = pd.read_csv('user_movie_df.csv', index_col=0)
        item_similarity_df = pd.read_csv('item_similarity.csv', index_col=0)

        user_item_matrix.index.name = 'id'

        # 加载 tfidf_matrix 和 indices
        tfidf_matrix = np.load('tfidf_matrix.npy')
        indices = pd.read_csv('movie_indices.csv', index_col=0)['title']

        # 加载相似度矩阵
        cosine_sim = np.load('cosine_similarity_matrix.npy')

        print("service is already running")
        logging.info('data loaded successfully.')
        logging.info('service is already running.')

        return user_item_matrix, item_similarity_df, tfidf_matrix, indices, cosine_sim

    def recommend_movies(self, user_id, top_n=10):
        # 获取用户已评分的电影及评分
        user_ratings = self.user_item_matrix.loc[user_id].dropna()
        # 初始化推荐得分
        scores = pd.Series(0.0, index=self.item_similarity_df.columns)

        # 遍历用户已评分的电影
        for movie, rating in user_ratings.items():
            # 获取与该电影相似的电影及其相似度
            if movie not in self.item_similarity_df.columns:
                continue
            similar_movies = self.item_similarity_df[movie] * rating
            # 根据用户对该电影的评分，计算推荐得分
            scores = scores.add(similar_movies, fill_value=0)

        # 移除用户已评分的电影
        scores = scores.drop(user_ratings.index)

        # 返回推荐得分最高的电影
        recommended_movies = scores.sort_values(ascending=False).head(top_n).index
        return recommended_movies

    def recommend_movies_by_movieId(self, movie_id, top_n=10):
        idx = self.indices[movie_id]
        sim_scores = list(enumerate(self.cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[1:11]  # 排除自身，取前10个相似电影
        movie_indices = [i[0] for i in sim_scores]
        return movie_indices

    def GetRecommendations(self, request, context):
        user_id = request.user_id
        print(f'GetRecommendations for user {user_id}')
        logging.info('request received: ', request)
        try:
            recommended_movies = self.recommend_movies(user_id)
            print(f'Recommended movies: {recommended_movies}')
            logging.info('Recommended movies: ', recommended_movies)
            return recommendation_pb2.RecommendationResponse(movie_ids=recommended_movies)
        except Exception as e:
            print(f'Error: {e}')
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.UNKNOWN)
            return recommendation_pb2.RecommendationResponse()

    def GetRecommendationsByMovieId(self, request, context):
        movie_id = request.movie_id
        print(f'GetRecommendationsByMovieId for movie {movie_id}')
        logging.info('request received: ', request)
        try:
            recommended_movies = self.recommend_movies_by_movieId(movie_id)
            print(f'Recommended movies: {recommended_movies}')
            logging.info('Recommended movies: ', recommended_movies)
            return recommendation_pb2.RecommendationResponse(movie_ids=recommended_movies)
        except Exception as e:
            print(f'Error: {e}')
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.UNKNOWN)
            return recommendation_pb2.RecommendationResponse()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    recommendation_pb2_grpc.add_RecommendationServiceServicer_to_server(RecommendationService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
