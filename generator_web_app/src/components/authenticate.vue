<script lang="ts">
import { defineComponent, ref, computed } from 'vue'; 
import { useUserStore } from '@/modules/stores/userStore';
import { useRouter, useRoute } from 'vue-router';

export default defineComponent({
    name: 'Authenticate',
    setup() {
        const user_store = (useUserStore());
        const router = useRouter();
        const route = useRoute();
        const redirection_path = route.query.redirect as string; 
  
        return { user_store, router, route, redirection_path }
    },
    data() {
        return {
            message: '',
            id_input: '',
        };
    },
    methods: {
        async establish_auth(external_id: string) {
            await this.user_store.authenticate(external_id)
            if (this.user_store.logged_in) {
                if (this.redirection_path) {
                    this.router.push(this.redirection_path);
                }
                else {
                    this.router.push('/');
                }
            } else {

            }
        },
    },
   
    async mounted() {        
        await this.user_store.check_auth();
        if (this.user_store.logged_in == true) {
            this.router.push('/')
        } 
    },
}); 
</script>

<template>
    <div class="pageContainer">
        <div id="auth-wrapper">
            <div id="wrapper-title">
                <h2> Authentication Required </h2>
                
            </div>
            <form id="auth-input">
                <label for="token_input"> Enter your access token: </label>
                <input type="password" id="token_input" v-model="id_input" autocomplete="off" >
            </form>
             <button @click="establish_auth(id_input)"> Authenticate </button>
        </div>
    </div>
</template>
<style scoped>
    #wrapper-title {
        display: flex;
        justify-content: center;
        align-items: center;
        background-color: var(--wygf-bg-blue);
        color: var(--wygf-yellow);
        width: 100%;
        height: 100%;
        max-height: 10vh;
        border-radius: 8px 8px 0px 0px;
        padding: 1%;
        font-size: 0.75em;
    }
    #auth-wrapper {
        background-color: var(--color-background-mute);
        height: 50vh;
        min-width: 25vw;
        display: flex;
        flex-direction: column;
        justify-content: center;      
        align-items: center;   
        border-radius: 8px;
        box-shadow: 0 8px 12px 4px var(--color-background);
    }
    #auth-input {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        height: 100%;
        width: 100%;
        padding: 2.5%;
        gap: 10px
    }
    #auth-input label {
        font-size: 1em;
    }
    #auth-input input {
        border-radius: 8px;
        width: 90%;
    }
    #auth-wrapper button {
        background-color: var(--wygf-bg-blue);
        border: none;
        color: var(--color-text);
        font-weight: bold;
        border-radius: 0 0 8px 8px;
        width: 100%;
        height: 15vh;
        margin-top: auto;
    }
    #auth-wrapper button:hover {
        background-color: var(--wygf-yellow);
        color: var(--wygf-bg-blue)
    }
</style>