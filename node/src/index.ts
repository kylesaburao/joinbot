import { Client, Events, GatewayIntentBits } from 'discord.js';

/**
 * SETUP:
 * - Add custom role for TARGET_ROLE_NAME
 * - Ensure bot role is above TARGET_ROLE_NAME
 */

const {
    DISCORD_BOT_TOKEN = undefined,
    DEV_MODE = false,
    TARGET_VC_CHANNEL_ID = '',
    TARGET_ROLE_NAME = '',
    GUILD_ID = ''
} = process.env;

if ([DISCORD_BOT_TOKEN, TARGET_VC_CHANNEL_ID, TARGET_ROLE_NAME, GUILD_ID].some(x => !x)) {
    throw new Error('Invalid .env config');
}

const getBotToken = (): string | undefined => {
    return DISCORD_BOT_TOKEN;
};

const main = async () => {
    const botClient = new Client({
        intents: [
            GatewayIntentBits.Guilds,
            GatewayIntentBits.GuildMembers,
            // GatewayIntentBits.GuildMessages,
            GatewayIntentBits.GuildVoiceStates
        ],
    });

    let onInitSuccess: Function;
    const onInit = new Promise((res) => {
        onInitSuccess = res;
    });
    botClient.once(Events.ClientReady, () => {
        onInitSuccess();
    });
    await botClient.login(getBotToken());
    await onInit;
    console.log('Bot is running...');

    if (DEV_MODE === 'true' || DEV_MODE === '1') {
        botClient.on(Events.MessageCreate, (message) => {
            if (message.content === '!ping') {
                message.reply('Pong!');
            }
        });
    }

    const targetGuild = botClient.guilds.cache.find(g => g.id === GUILD_ID);
    if (!targetGuild) {
        throw new Error(`Could not find guild from ID ${GUILD_ID}`);
    }
    const targetRole = targetGuild.roles.cache.find(r => r.name === TARGET_ROLE_NAME);
    if (!targetRole) {
        throw new Error(`Could not find role from name ${TARGET_ROLE_NAME}`);
    }
    
    botClient.on(Events.VoiceStateUpdate, async (oldState, newState) => {
        const userId = newState.id;
        const newChannelId = newState.channelId;
        const now = new Date();

        const isJoinedTargetVCChannel = newChannelId === TARGET_VC_CHANNEL_ID;
        const isLeftTargetVCChannel = newChannelId !== TARGET_VC_CHANNEL_ID;

        try {
            if (isJoinedTargetVCChannel) {
                console.log(`${userId} joined ${newChannelId} @ ${now}`)
                if (newState.member && !newState.member.roles.cache.has(targetRole.id)) {
                    newState.member.roles.add(targetRole.id);
                }
            }
    
            if (isLeftTargetVCChannel) {
                console.log(`${userId} left ${newChannelId} @ ${now}`);
                if (newState.member && newState.member.roles.cache.has(targetRole.id)) {
                    newState.member.roles.remove(targetRole.id);
                }
            }
        } catch (error) {
            console.error('An error occured while processing role change:', error);
        }
    });
};

main().catch(error => {
    console.error('An error occurred:', error);
});
