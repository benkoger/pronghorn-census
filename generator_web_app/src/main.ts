import '@/assets/custom.scss'
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue-next/dist/bootstrap-vue-next.css'
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';
import App from './app.vue';
import router from './router';
import { Icon } from '@iconify/vue';
import VueKonva from 'vue-konva';
import { useUserStore } from './modules/stores/userStore';

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
const app = createApp(App);

app.use(pinia);
app.use(router);
app.use(VueKonva);

const userStore = useUserStore();

await userStore.check_auth();

app.component('Icon', Icon);

app.mount('#app');