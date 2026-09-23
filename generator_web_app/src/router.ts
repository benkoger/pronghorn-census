import { createRouter, createWebHistory } from "vue-router";
import Authenticate from "@/views/AuthView.vue";
import { useSystemStore, setSystemStoreRouter } from "@/stores/systemStore";
import { api } from "@/api";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/setup",
      name: "setup",
      component: () => import("@/views/SetupView.vue"),
      meta: {
        requiresAuth: false,
        requiresNoLayout: true,
      },
    },
    {
      path: "/authenticate",
      name: "authenticate",
      component: Authenticate,
      meta: { requiresNoLayout: true, requiresNoTitle: true },
    },
    {
      path: "/",
      name: "dashboard",
      component: () => import("@/views/DashboardView.vue"),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      },
    },
    // {
    //   path: "/users/:uuid?",
    //   name: "users",
    //   component: () => import("@/views/UsersView.vue"),
    //   meta: {
    //     requiresAuth: true,
    //     requiresNoLayout: false,
    //   },
    // },
    {
      path: "/auto-cropper/",
      name: "auto-cropper",
      component: () => import("@/views/AutoCropperView.vue"),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      },
    },
    {
      path: "/crop-verifier/",
      name: "crop-verifier",
      component: () => import("@/views/CropVerifierView.vue"),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      },
    },
    {
      path: "/active-measurement/",
      name: "active-measurement",
      component: () => import("@/views/ActiveMeasurementView.vue"),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      }
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("@/views/SettingsView.vue"),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      },
    },
    {
      path: "/upload/",
      name: "upload",
      component: () => import("@/views/UploaderView.vue"),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      },
    },
  ],
});

router.beforeEach(async (to) => {
  const sStore = useSystemStore();

  if (sStore.bootstrapped === undefined) {
    const data = await api.get<{ result: boolean }>("bootstrapped").catch(() => undefined);
    sStore.bootstrapped = Boolean(data?.result);
  }

  if (!sStore.bootstrapped) {
    return to.name === "setup" ? true : { name: "setup" };
  }

  if (sStore.bootstrapped && to.name === "setup") {
    return { name: "authenticate" };
  }

  if (to.meta.requiresAuth) {
    if (!sStore.logged_in) {
      await sStore.check_auth();
    }

    if (!sStore.logged_in) {
      return {
        name: "authenticate",
        query: { redirect: to.fullPath },
      };
    }
    await sStore.check_admin();
  }

  return true;
});

setSystemStoreRouter(router);

router.afterEach((to) => {
  const sStore = useSystemStore();
  sStore.syncFromRoute(to);
});

export default router;
