import asyncio
import datetime
from unicodedata import mirrored

import discord

import config


class ServerCloner:

    def __init__(self, token: str, original_guild_id: int, new_guild_id: int, cleaning_interval: float = .7, cloning_interval: float = .7, emoji_cloning_interval: float = 2):
        self.client = discord.Client()
        self.original_guild_id = original_guild_id
        self.new_guild_id = new_guild_id
        self.cleaning_interval = cleaning_interval
        self.cloning_interval = cloning_interval
        self.emoji_cloning_interval = emoji_cloning_interval
        self.token = token
        self.original_guild = None
        self.new_guild = None
        self.mirror_roles = {}
        self.mirror_channels = {}
        self.is_community = False

    def clone(self):
        print('> Logging in...')

        @self.client.event
        async def on_ready():
            print()
            print()
            print(f'> 👤 | Logged in as {self.client.user}')
            self.original_guild = self.client.get_guild(self.original_guild_id)
            self.new_guild = self.client.get_guild(self.new_guild_id)
            self.is_community = self.new_guild.rules_channel is not None and self.new_guild.public_updates_channel is not None
            estimated_time = self.get_estimated_cloning_time()
            m, s = divmod(estimated_time, 60)
            print(f'> 🕘 | Estimated Cloning Time: {m}m {s}s')
            print()
            print()
            start_time = datetime.datetime.now()

            def _log_task_exc(t: asyncio.Task):
                if t.cancelled():
                    return
                try:
                    t.result()
                except Exception as e:
                    print(f'> ⚠️ | Task error: {e}')

            await self.edit_guild_settings()
            tasks = []
            if config.clone_options['enable_community']:
                await self.disable_community()
            if config.clone_options['clean_emojis']:
                task_clean_emojis = asyncio.create_task(self.clean_emojis())
                task_clean_emojis.add_done_callback(_log_task_exc)
                tasks.append(task_clean_emojis)
            if config.clone_options['clone_emojis']:
                task_clone_emojis = asyncio.create_task(self.clone_emojis())
                task_clone_emojis.add_done_callback(_log_task_exc)
                tasks.append(task_clone_emojis)
            if config.clone_options['set_icon']:
                await self.edit_guild_icon()
            if config.clone_options['set_banner']:
                await self.edit_guild_banner()
            if config.clone_options['clean_roles']:
                if self.cleaning_interval >= 0.7:
                    task_clean_roles = asyncio.create_task(self.clean_roles())
                    task_clean_roles.add_done_callback(_log_task_exc)
                    tasks.append(task_clean_roles)
                else:
                    await self.clean_roles()
            if config.clone_options['clean_channels']:
                if self.cleaning_interval >= 0.7:
                    task_clean_channels = asyncio.create_task(self.clean_channels())
                    task_clean_channels.add_done_callback(_log_task_exc)
                    tasks.append(task_clean_channels)
                else:
                    await self.clean_channels()
            if config.clone_options['clone_roles']:
                await self.clone_roles()
            if config.clone_options['clone_channels']:
                await self.clone_categories()
                await self.clone_text_channels()
                await self.clone_voice_channels()
            if config.clone_options['edit_guild_channel_settings']:
                await self.edit_guild_channel_settings()
            if config.clone_options['enable_community']:
                await self.enable_community()
                await self.convert_channels_to_news()
            if self.is_community:
                if config.clone_options['clone_channels']:
                    await self.clone_forum_channels()
                    await self.clone_stage_channels()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            print()
            print()
            print('> ✅ | Server Cloned Successfully')
            t = int((datetime.datetime.now() - start_time).total_seconds())
            m, s = divmod(t, 60)
            print(f'> 🕘 | Time Used: {m}m {s}s')
            print('> ↩️️ | Logging out')
            try:
                await self.client.close()
            except Exception as e:
                pass
        self.client.run(self.token)

    async def edit_guild_icon(self, retries: int = 5):
        success = False
        for _ in range(retries):
            icon = self.original_guild.icon
            if icon is not None:
                icon = await icon.read()
            try:
                await self.new_guild.edit(icon=icon)
                success = True
                break
            except Exception as e:
                self.original_guild = self.client.get_guild(self.original_guild_id)
                self.new_guild = self.client.get_guild(self.new_guild_id)
                await asyncio.sleep(5)
                continue
        if success:
            print(f'> 🖼️ | Guild Icon Edited')
        else:
            print(f'> ⚠️ | Failed to edit Guild Icon')

    async def edit_guild_banner(self, retries: int = 5):
        success = False
        for _ in range(retries):
            banner = self.original_guild.banner
            if banner is not None:
                banner = await banner.read()
            try:
                await self.new_guild.edit(banner=banner)
                success = True
                break
            except Exception as e:
                self.original_guild = self.client.get_guild(self.original_guild_id)
                self.new_guild = self.client.get_guild(self.new_guild_id)
                await asyncio.sleep(5)
                continue
        if success:
            print(f'> 🌆 | Guild Banner Edited')
        else:
            print(f'> ⚠️ | Failed to edit Guild Banner')

    async def edit_guild_settings(self):
        try:
            await self.new_guild.edit(name=self.original_guild.name,
                                      description=self.original_guild.description,
                                      afk_timeout=self.original_guild.afk_timeout,
                                      verification_level=self.original_guild.verification_level,
                                      explicit_content_filter=self.original_guild.explicit_content_filter,
                                      default_notifications=self.original_guild.default_notifications,
                                      system_channel_flags=self.original_guild.system_channel_flags,
                                      preferred_locale=self.original_guild.preferred_locale,
                                      premium_progress_bar_enabled=self.original_guild.premium_progress_bar_enabled,
                                      )
            print(f'> ⚙️ | Guild Settings Edited')
        except Exception as e:
            print(f'> ⚠️ | Failed to edit Guild Settings')

    async def edit_guild_channel_settings(self):
        try:
            afk_channel = None
            if self.original_guild.afk_channel is not None:
                afk_channel = self.mirror_channels[self.original_guild.afk_channel]
            system_channel = None
            if self.original_guild.system_channel is not None:
                system_channel = self.mirror_channels[self.original_guild.system_channel]
            await self.new_guild.edit(afk_channel=afk_channel,
                                      system_channel=system_channel)
            print(f'> ⚙️ | Guild Channel Settings Edited')
        except Exception as e:
            print(f'> ⚠️ | Failed to edit Guild Channel Settings')

    async def disable_community(self):
        try:
            await self.new_guild.edit(community=False)
            self.is_community = False
            print(f'> ⚙️ | Community Disabled')
        except Exception as e:
            print(f'> ⚠️ | Failed to disable community')

    async def enable_community(self):
        try:
            if self.original_guild.rules_channel is not None and self.original_guild.public_updates_channel is not None:
                self.is_community = True
                rules_channel = None
                public_updates_channel = None
                if self.original_guild.rules_channel is not None:
                    rules_channel = self.mirror_channels[self.original_guild.rules_channel]
                if self.original_guild.public_updates_channel is not None:
                    public_updates_channel = self.mirror_channels[self.original_guild.public_updates_channel]
                await self.new_guild.edit(community=True,
                                          rules_channel=rules_channel,
                                          public_updates_channel=public_updates_channel)
                print(f'> ⚙️ | Community Enabled')
        except Exception as e:
            print(f'> ⚠️ | Failed to enable community')

    async def clean_roles(self):
        print('> 🧹 | Cleaning roles')
        len_objects = len(self.new_guild.roles)
        for i, role in enumerate(self.new_guild.roles):
            try:
                if not role.is_default() and not role.is_bot_managed() and not role.is_premium_subscriber() and not role.is_integration():
                    await role.delete()
                    print(f'- ❌ | ({i+1}/{len_objects}) Role deleted: {role.name}')
                await asyncio.sleep(self.cleaning_interval)
            except Exception as e:
                print(e)
                print(f'- ⚠️ | ({i+1}/{len_objects}) Failed to delete role: {role.name}')

    async def clone_roles(self):
        print(f'> 🧬 | Cloning roles')
        for i, role in enumerate(self.original_guild.roles[::-1]):
            try:
                if not role.is_default() and not role.is_bot_managed() and not role.is_premium_subscriber() and not role.is_integration():
                    cloned_role = await self.new_guild.create_role(name=role.name, permissions=role.permissions,
                                                                   color=role.color, mentionable=role.mentionable,
                                                                   hoist=role.hoist)
                    self.mirror_roles[role] = cloned_role
                    print(f'- ➕ | ({i+1}/{len(self.original_guild.roles)}) Role cloned: {cloned_role.name}')
                    await asyncio.sleep(self.cloning_interval)
                elif role.is_default():
                    await self.new_guild.default_role.edit(permissions=role.permissions)
                    print(f'- ➕ | ({i+1}/{len(self.original_guild.roles)}) Changed Permissions for Default Role')
                    await asyncio.sleep(self.cloning_interval)
                elif role.is_premium_subscriber():
                    for new_guild_role in self.new_guild.roles:
                        if new_guild_role.is_premium_subscriber():
                            await new_guild_role.edit(permissions=role.permissions)
                            print(f'- ➕ | ({i+1}/{len(self.original_guild.roles)}) Changed Permissions for Premium Subscriber Role')
                            await asyncio.sleep(self.cloning_interval)
            except Exception as e:
                print(e)
                print(f'- ⚠️ | ({i+1}/{len(self.original_guild.roles)}) Failed to clone role: {role.name}')

    async def clean_channels(self):
        print('> 🧹 | Cleaning channels')
        len_objects = len(self.new_guild.channels)
        channels = self.new_guild.channels
        for i, channel in enumerate(channels):
            start_time = datetime.datetime.now()

            try:
                await channel.delete()
                print(f'- ❌ | ({i+1}/{len_objects}) Channel deleted: {channel.name}')
                await asyncio.sleep(self.cleaning_interval)
            except Exception as e:
                print(e)
                print(f'- ⚠️ | ({i+1}/{len_objects}) Failed to delete channel: {channel.name}')

    async def clone_categories(self):
        print(f'> 🧬 | Cloning categories')
        channels = self.original_guild.categories
        for i, category in enumerate(channels):
            try:
                cloned_category = await self.clone_category(category)
                self.mirror_channels[category] = cloned_category
                print(f'- ➕ | ({i+1}/{len(channels)}) Category cloned: {cloned_category.name}')
                await asyncio.sleep(self.cloning_interval)
            except Exception as e:
                print(f'- ⚠️ | ({i+1}/{len(channels)}) Failed to clone category: {category.name}')

    async def clone_text_channels(self):
        print(f'> 🧬 | Cloning text channels')
        channels = self.original_guild.text_channels
        for i, channel in enumerate(channels):
            try:
                cloned_channel = await self.clone_text_channel(channel)
                self.mirror_channels[channel] = cloned_channel
                print(f'- ➕ | ({i+1}/{len(channels)}) Text Channel cloned: {cloned_channel.name}')
                await asyncio.sleep(self.cloning_interval)
            except Exception as e:
                print(f'- ⚠️ | ({i+1}/{len(channels)}) Failed to clone text channel: {channel.name}')

    async def clone_voice_channels(self):
        print(f'> 🧬 | Cloning voice channels')
        channels = self.original_guild.voice_channels
        for i, channel in enumerate(channels):
            try:
                cloned_channel = await self.clone_voice_channel(channel)
                self.mirror_channels[channel] = cloned_channel
                print(f'- ➕ | ({i+1}/{len(channels)}) Voice Channel cloned: {cloned_channel.name}')
                await asyncio.sleep(self.cloning_interval)
            except Exception as e:
                print(f'- ⚠️ | ({i+1}/{len(channels)}) Failed to clone voice channel: {channel.name}')

    async def clone_forum_channels(self):
        print(f'> 🧬 | Cloning forum channels')
        channels = self.original_guild.forums
        for i, channel in enumerate(channels):
            try:
                cloned_channel = await self.clone_forum_channel(channel)
                self.mirror_channels[channel] = cloned_channel
                print(f'- ➕ | ({i+1}/{len(channels)}) Forum Channel cloned: {cloned_channel.name}')
                await asyncio.sleep(self.cloning_interval)
            except Exception as e:
                print(e)
                print(f'- ⚠️ | ({i+1}/{len(channels)}) Failed to clone forum channel: {channel.name}')

    async def clone_stage_channels(self):
        print(f'> 🧬 | Cloning stage channels')
        channels = self.original_guild.stage_channels
        for i, channel in enumerate(channels):
            try:
                cloned_channel = await self.clone_stage_channel(channel)
                self.mirror_channels[channel] = cloned_channel
                print(f'- ➕ | ({i+1}/{len(channels)}) Stage Channel cloned: {cloned_channel.name}')
                await asyncio.sleep(self.cloning_interval)
            except Exception as e:
                print(f'- ⚠️ | ({i+1}/{len(channels)}) Failed to clone stage channel: {channel.name}')

    async def convert_channels_to_news(self):
        print(f'> 🧬 | Converting News Channels')
        channels = self.original_guild.text_channels
        for i, channel in enumerate(channels):
            try:
                if channel.is_news():
                    await self.mirror_channels[channel].edit(type=discord.ChannelType.news)
                    print(f'- ➕ | Channel Converted to News: {channel.name}')
            except Exception as e:
                print(f'- ⚠️ | Failed to convert channel to news: {channel.name}')

    async def clone_category(self, category):
        start_time = datetime.datetime.now()
        cloned_category = await self.new_guild.create_category(name=category.name, overwrites=category.overwrites)
        await self.__set_overwrites_for_channel(category, cloned_category)
        return cloned_category

    async def clone_text_channel(self, channel):
        category = self.__get_channel_category(channel)
        cloned_channel = await self.new_guild.create_text_channel(channel.name, category=category,
                                                                   position=channel.position,
                                                                   nsfw=channel.is_nsfw(), topic=channel.topic,
                                                                   slowmode_delay=channel.slowmode_delay,
                                                                   default_auto_archive_duration=channel.default_auto_archive_duration,
                                                                   default_thread_slowmode_delay=channel.default_thread_slowmode_delay)
        await self.__set_overwrites_for_channel(channel, cloned_channel)
        return cloned_channel

    async def clone_voice_channel(self, channel):
        category = self.__get_channel_category(channel)
        cloned_channel = await self.new_guild.create_voice_channel(channel.name, category=category,
                                                                   position=channel.position,
                                                                   bitrate=channel.bitrate if channel.bitrate <= 96000 else 96000,
                                                                   user_limit=channel.user_limit, rtc_region=channel.rtc_region,
                                                                   video_quality_mode=channel.video_quality_mode)
        await self.__set_overwrites_for_channel(channel, cloned_channel)
        return cloned_channel

    async def clone_forum_channel(self, channel):
        category = self.__get_channel_category(channel)
        additional_kwargs = {}
        if channel.default_sort_order is not None:
            additional_kwargs['default_sort_order'] = channel.default_sort_order
        if channel.default_reaction_emoji is not None:
            additional_kwargs['default_reaction_emoji'] = channel.default_reaction_emoji
        if channel.default_layout is not None:
            additional_kwargs['default_layout'] = channel.default_layout
        if channel.available_tags is not None:
            additional_kwargs['available_tags'] = channel.available_tags
        cloned_channel = await self.new_guild.create_forum(channel.name, category=category,
                                                                   position=channel.position,
                                                                   topic=channel.topic,
                                                                   slowmode_delay=channel.slowmode_delay,
                                                                   default_auto_archive_duration=channel.default_auto_archive_duration,
                                                                   default_thread_slowmode_delay=channel.default_thread_slowmode_delay,
                                                                   **additional_kwargs)
        await self.__set_overwrites_for_channel(channel, cloned_channel)
        return cloned_channel

    async def clone_stage_channel(self, channel):
        category = self.__get_channel_category(channel)
        cloned_channel = await self.new_guild.create_stage_channel(channel.name, category=category,
                                                                   position=channel.position,
                                                                   bitrate=channel.bitrate if channel.bitrate <= 96000 else 96000,
                                                                   user_limit=channel.user_limit, rtc_region=channel.rtc_region,
                                                                   video_quality_mode=channel.video_quality_mode)
        await self.__set_overwrites_for_channel(channel, cloned_channel)
        return cloned_channel

    async def clean_emojis(self):
        print(f'> 🧹 | Cleaning Emojis')
        for i, emoji in enumerate(self.new_guild.emojis):
            try:
                await emoji.delete()
                print(f'- ❌ | ({i+1}/{len(self.new_guild.emojis)}) Emoji deleted: {emoji.name}')
                await asyncio.sleep(self.emoji_cloning_interval)
            except Exception as e:
                print(f'- ⚠️ | ({i+1}/{len(self.new_guild.emojis)}) Failed to delete emoji: {emoji.name}')

    async def clone_emojis(self):
        print(f'> 🧬 | Cloning Emojis')
        len_objects = len(self.new_guild.emojis)
        for i, emoji in enumerate(self.original_guild.emojis):
            try:
                if i < self.original_guild.emoji_limit:
                    for _ in range(3):
                        try:
                            emoji_image = await emoji.read()
                            cloned_emoji = await self.new_guild.create_custom_emoji(name=emoji.name, image=emoji_image)
                            print(f'- ➕ | ({i+1}/{len_objects}) Emoji cloned: {cloned_emoji.name}')
                            break
                        except Exception as e:
                            continue
                else:
                    return
                await asyncio.sleep(self.emoji_cloning_interval)
            except Exception as e:
                print(f'- ⚠️ | ({i+1}/{len_objects}) Failed to clone emoji: {emoji.name}')

    def get_estimated_cloning_time(self):
        cloning_time_per_channel = []

        if config.clone_options['clone_channels']:
            for i, channel in enumerate(self.original_guild.channels):
                cloning_time_per_channel.append(self.cloning_interval + 0.4)
                for role in self.original_guild.roles:
                    if not all([i is None for i in
                            ServerCloner.__permissions_to_dict(channel.overwrites_for(role)).values()]):
                        cloning_time_per_channel[i] += 0.16

        cloning_time_per_role = []
        if config.clone_options['clone_roles']:
            for role in self.original_guild.roles:
                if not role.is_bot_managed() and not role.is_integration():
                    cloning_time_per_role.append(self.cloning_interval + 0.3)

        roles_deletion_time = len(self.new_guild.roles) * (self.cloning_interval + 0.25) if config.clone_options['clean_roles'] else 0
        roles_cloning_time = sum(cloning_time_per_role) if config.clone_options['clone_roles'] else 0
        channels_deletion_time = len(self.new_guild.channels) * (self.cloning_interval + 0.25) if config.clone_options['clean_channels'] else 0
        channels_cloning_time = sum(cloning_time_per_channel) if config.clone_options['clone_channels'] else 0
        emoji_deletion_time = len(self.new_guild.emojis) * (self.emoji_cloning_interval + 0.25) if config.clone_options['clean_emojis'] else 0
        emoji_cloning_time = len(self.original_guild.emojis) * (self.emoji_cloning_interval + 0.3) if config.clone_options['clone_emojis'] else 0

        full_emoji_processing_time = emoji_cloning_time if emoji_cloning_time > emoji_deletion_time else emoji_deletion_time
        full_roles_and_channels_cloning_processing_time = roles_cloning_time + channels_cloning_time

        l = [full_emoji_processing_time]

        if self.cleaning_interval < .7:
            full_roles_and_channels_cloning_processing_time += roles_deletion_time + channels_deletion_time
            l.append(full_roles_and_channels_cloning_processing_time)
        else:
            l += [full_roles_and_channels_cloning_processing_time, roles_deletion_time, channels_deletion_time]

        return int(max(l))

    def __get_channel_category(self, channel):
        if channel.category is None:
            category = None
        else:
            category = self.mirror_channels[channel.category]
        return category

    async def __set_overwrites_for_channel(self, original_channel: discord.TextChannel, cloned_channel: discord.TextChannel):
        for role in self.original_guild.roles:
            if all([i is None for i in ServerCloner.__permissions_to_dict(original_channel.overwrites_for(role)).values()]):
                continue
            if not role.is_default() and not role.is_bot_managed() and not role.is_premium_subscriber() and not role.is_integration():
                overwrite = original_channel.overwrites_for(role)
                new_guild_role = self.mirror_roles.get(role)
                if new_guild_role is None:
                    continue
                await cloned_channel.set_permissions(new_guild_role, overwrite=overwrite)
            elif role.is_default():
                overwrite = original_channel.overwrites_for(self.original_guild.default_role)
                await cloned_channel.set_permissions(self.new_guild.default_role, overwrite=overwrite)
            elif role.is_premium_subscriber():
                for new_guild_role in self.new_guild.roles:
                    if new_guild_role.is_premium_subscriber():
                        overwrite = original_channel.overwrites_for(new_guild_role)
                        await cloned_channel.set_permissions(new_guild_role, overwrite=overwrite)

    @staticmethod
    def __permissions_to_dict(permissions):
        permissions_dict = {}
        for name in dir(permissions):
            attribute = getattr(permissions, name)
            try:
                if attribute in [True, False, None]:
                    permissions_dict[name] = attribute
            except:
                pass
        return permissions_dict
