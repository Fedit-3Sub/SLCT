import Vue from 'vue';
import App from '@/App.vue';
import router from './router';
import store from "./store";
import "@/registerServiceWorker";

import '@/assets/css/diagram-js.css'
import '@/assets/css/bpmn-js.css'
import '@/assets/css/bpmn-embedded.css'
import '@/assets/css/properties-panel.css'
import '@/assets/css/color-picker.css'
import '@/assets/css/bpmn-js-token-simulation.css'
import '@/assets/css/main.css'

import { CHECK_AUTH } from "./store/actions.type";
import ApiService from "./common/api.service";
import DateFilter from "./common/date.filter";
import ErrorFilter from "./common/error.filter";

Vue.config.productionTip = false
Vue.config.devtools = true
Vue.filter("date", DateFilter);
Vue.filter("error", ErrorFilter);
ApiService.init();

router.beforeEach((to, from, next) =>
  Promise.all([store.dispatch(CHECK_AUTH)]).then(next)
);

/* eslint-disable no-new */
new Vue({
  router,
  store,
  render: h => h(App),
}).$mount("#app");
