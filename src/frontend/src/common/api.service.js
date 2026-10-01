import Vue from "vue";
import axios from "axios";
import VueAxios from "vue-axios";
import JwtService from "@/common/jwt.service";
import { API_URL } from "@/common/config";

const EDIT_TOKEN_KEY = "slct-edit-token";

/**
 * 편집 토큰을 준비한다.
 *
 * 주소에 ?token=... 이 있으면 브라우저에 저장하고, 주소창에도 그대로 남겨 둔다
 * (북마크·새로고침해도 편집 권한이 유지되도록). 이후 모든 API 요청에
 * X-SLCT-Token 헤더로 붙인다. 토큰이 없으면 보기 전용으로 동작한다.
 * 주의: 토큰이 든 주소를 공유하면 편집 권한도 함께 넘어간다.
 */
function setupEditToken() {
  let token = "";
  try {
    const url = new URL(window.location.href);
    const fromUrl = url.searchParams.get("token");
    if (fromUrl !== null) {
      if (fromUrl) window.localStorage.setItem(EDIT_TOKEN_KEY, fromUrl);
      else window.localStorage.removeItem(EDIT_TOKEN_KEY); // ?token= 로 비우면 토큰 삭제
    }
    token = window.localStorage.getItem(EDIT_TOKEN_KEY) || "";
  } catch (e) {
    token = "";
  }
  if (token) {
    axios.defaults.headers.common["X-SLCT-Token"] = token;
  }
}

const ApiService = {
  init() {
    setupEditToken();
    Vue.use(VueAxios, axios);
    Vue.axios.defaults.baseURL = API_URL;
  },

  setHeader() {
    Vue.axios.defaults.headers.common[
      "Authorization"
    ] = `Token ${JwtService.getToken()}`;
  },

  query(resource, params) {
    return Vue.axios.get(resource, params).catch(error => {
      throw new Error(`[RWV] ApiService ${error}`);
    });
  },

  get(resource, slug = "") {
    const url = slug ? `${resource}/${slug}` : resource;
    return Vue.axios.get(url).catch(error => {
      throw new Error(`[RWV] ApiService ${error}`);
    });
  },

  post(resource, params) {
    return Vue.axios.post(`${resource}`, params);
  },

  update(resource, slug, params) {
    return Vue.axios.put(`${resource}/${slug}`, params);
  },

  put(resource, params) {
    return Vue.axios.put(`${resource}`, params);
  },

  delete(resource) {
    return Vue.axios.delete(resource).catch(error => {
      throw new Error(`[RWV] ApiService ${error}`);
    });
  }
};

export default ApiService;

export const TagsService = {
  get() {
    return ApiService.get("tags");
  }
};

export const ArticlesService = {
  query(type, params) {
    return ApiService.query("articles" + (type === "feed" ? "/feed" : ""), {
      params: params
    });
  },
  get(slug) {
    return ApiService.get("articles", slug);
  },
  create(params) {
    return ApiService.post("articles", { article: params });
  },
  update(slug, params) {
    return ApiService.update("articles", slug, { article: params });
  },
  destroy(slug) {
    return ApiService.delete(`articles/${slug}`);
  }
};

export const CommentsService = {
  get(slug) {
    if (typeof slug !== "string") {
      throw new Error(
        "[RWV] CommentsService.get() article slug required to fetch comments"
      );
    }
    return ApiService.get("articles", `${slug}/comments`);
  },

  post(slug, payload) {
    return ApiService.post(`articles/${slug}/comments`, {
      comment: { body: payload }
    });
  },

  destroy(slug, commentId) {
    return ApiService.delete(`articles/${slug}/comments/${commentId}`);
  }
};

export const FavoriteService = {
  add(slug) {
    return ApiService.post(`articles/${slug}/favorite`);
  },
  remove(slug) {
    return ApiService.delete(`articles/${slug}/favorite`);
  }
};
