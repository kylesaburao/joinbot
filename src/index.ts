import { Client, Events, GatewayIntentBits } from 'discord.js';
import { userVoiceData } from './db/store';

const getBotToken = (): string => {
    const token = process.env.DISCORD_BOT_TOKEN;
    if (!token) {
        throw new Error('DISCORD_BOT_TOKEN environment variable is not set.');
    }
    return token;
};

const main = async (): Promise<void> => {
    const client = new Client({
        intents: [
            GatewayIntentBits.Guilds,
            GatewayIntentBits.GuildMessages,
            GatewayIntentBits.MessageContent,
            GatewayIntentBits.GuildVoiceStates,
        ],
    });

    client.once(Events.ClientReady, (readyClient) => {
        console.log(`Ready! Logged in as ${readyClient.user.tag}`);
    });
    await client.login(getBotToken());

    client.on(Events.MessageCreate, (message) => {
        if (message.content === '!ping') {
            message.reply('Pong!');
        }

        if (message.content === '!leaderboard') {
            const leaderboard = Array.from(userVoiceData.values())
                .sort((a, b) => b.accumulatedTime - a.accumulatedTime)
                .slice(0, 10)
                .map((data, index) => {
                    const timeInSeconds = Math.floor(data.accumulatedTime / 1000);
                    return `${index + 1}. <@${data.userId}> - ${timeInSeconds} seconds`;
                })
                .join('\n');

            message.reply(`Voice Channel Leaderboard:\n${leaderboard}`);
        }
    });
    
    client.on(Events.VoiceStateUpdate, async (oldState, newState) => {
        const userId = newState.id;
        const isChannelJoined = oldState.channelId === null && newState.channelId !== null;
        const isChannelLeft = oldState.channelId !== null && newState.channelId === null;
        const isChannelSwitched = oldState.channelId !== null && newState.channelId !== null && oldState.channelId !== newState.channelId;
        const now = new Date();

        if (isChannelLeft || isChannelSwitched) {
            const userData = userVoiceData.get(userId);

            if (userData) { // false -> user didn't join before this point so there's nothing to do
                const timeSpentInCurrentChannel = now.getTime() - userData.lastJoin.getTime();
                userData.accumulatedTime += timeSpentInCurrentChannel;

                const REPORT_CHANNEL = '<SET>';
                const channel = await client.channels.fetch(REPORT_CHANNEL);
                if (channel && channel.isTextBased() && channel.isSendable()) {
                    const channelName = oldState.channel?.name || 'Unknown Channel';
                    const timeSpentSinceContiguousJoin = Math.floor(timeSpentInCurrentChannel / 1000);
                    const timeSpentTotal = Math.floor(userData.accumulatedTime / 1000);
                    const message = `<@${userId}> has spent ${timeSpentSinceContiguousJoin} seconds in ${channelName} since joining, and a total of ${timeSpentTotal} seconds in voice chat.`;
                    await channel.send(message);
                }

                if (isChannelSwitched) {
                    userData.lastJoin = now;
                    userData.lastChannelIdJoined = newState.channelId!;
                }

                userVoiceData.set(userId, userData);
            }
        }

        if (isChannelJoined) {
            const existingData = userVoiceData.get(userId);
            userVoiceData.set(userId, {
                userId,
                lastJoin: now,
                lastChannelIdJoined: newState.channelId!,
                accumulatedTime: existingData?.accumulatedTime ?? 0,
            });
        }
    });
};

main().catch(error => {
    console.error('An error occurred:', error);
});
