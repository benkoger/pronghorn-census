import { createRouter, createWebHistory } from 'vue-router';
import Authenticate from '@/pages/authenticate.vue';
import { useUserStore } from '@/modules/stores/userStore';


const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/setup',
      name: 'setup',
      component: () => import('@/pages/intialSetup.vue'),
      meta: {
        requiresAuth: false,
        requiresNoLayout: true
      },
    },
    {
      path: '/authenticate',
      name: 'authenticate',
      component: Authenticate,
      meta: { requiresNoLayout: true },
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/pages/dashboard.vue'),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      },
    },
    {
      path: '/users/:uuid?',
      name: 'users',
      component: () => import('@/pages/users.vue'),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      },
    },
    {
      path: '/auto-cropper/',
      name: 'auto-cropper',
      component: () => import('@/pages/autoCropper/autoCropperPage.vue'),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      },
    },
    {
      path: '/crop-verifier/',
      name: 'crop-verifier',
      component: () => import('@/pages/cropVerifier/cropVerifierPage.vue'),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/pages/settings.vue'),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      },
    },
    {
      path: '/statistics',
      name: 'statistics',
      component: () => import('@/pages/statistics.vue'),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      },
    },
    {
      path: '/upload/',
      name: 'upload',
      component: () => import('@/pages/uploader/uploaderPage.vue'),
      meta: {
        requiresAuth: true,
        requiresNoLayout: false,
      }
    }
  ],
});

router.beforeEach(async (to, from, next) => {
  const user_store = useUserStore();

  if (to.meta.requiresAuth) {

    if (user_store.logged_in) {
      next();
    } else {
      await user_store.check_auth();
      if (user_store.logged_in) {
        next();
      } else {
        next({
          name: 'authenticate',
          query: { redirect: to.fullPath },
        });
      }
    }
  } else {
    next()
  }
});


export default router;
