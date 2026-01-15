import asyncio

import discord


class ServerCloner:

    def __init__(self, token: str, original_guild_id: int, new_guild_id: int, copy_interval: float = .7):
        self.client = discord.Client()
        self.original_guild_id = original_guild_id
        self.new_guild_id = new_guild_id
        self.copy_interval = copy_interval
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
            print(f'> Logged in as {self.client.user}')
            self.original_guild = self.client.get_guild(self.original_guild_id)
            self.new_guild = self.client.get_guild(self.new_guild_id)
            task_clean_emojis = asyncio.create_task(self.clean_emojis())
            task_clone_emojis = asyncio.create_task(self.clone_emojis())

            def _log_task_exc(t):
                try:
                    t.result()
                except Exception as e:
                    print(f'Emoji task error: {e}')

            task_clean_emojis.add_done_callback(_log_task_exc)
            task_clone_emojis.add_done_callback(_log_task_exc)
            await self.edit_guild_icon()
            await self.disable_community()
            await self.clean_roles()
            await self.clone_roles()
            await self.clean_channels()
            await self.clone_categories()
            await self.clone_text_channels()
            await self.clone_voice_channels()
            await self.edit_guild_settings()
            await self.enable_community()
            if self.is_community:
                await self.clone_forum_channels()
                await self.clone_stage_channels()
            print('> Server Cloned Successfully')
            print('> Logging out')
            await self.client.close()
        self.client.run(self.token)

    async def edit_guild_icon(self, retries: int = 3):
        for _ in range(retries):
            icon = self.original_guild.icon
            if icon is not None:
                icon = await icon.read()
            try:
                await self.new_guild.edit(icon=icon)
                break
            except Exception as e:
                await asyncio.sleep(1)
                continue
        print(f'> 🖼️ | Guild Icon Edited')

    async def edit_guild_banner(self, retries: int = 3):
        for _ in range(retries):
            banner = self.original_guild.banner
            if banner is not None:
                banner = await banner.read()
            try:
                await self.new_guild.edit(icon=banner)
                break
            except Exception as e:
                await asyncio.sleep(1)
                continue
        print(f'> 🌆 | Guild Banner Edited')

    async def edit_guild_settings(self):
        afk_channel = None
        if self.original_guild.afk_channel is not None:
            afk_channel = self.mirror_channels[self.original_guild.afk_channel]
        system_channel = None
        if self.original_guild.system_channel is not None:
            system_channel = self.mirror_channels[self.original_guild.system_channel]
        await self.new_guild.edit(name=self.original_guild.name,
                                  description=self.original_guild.description,
                                  afk_channel=afk_channel,
                                  afk_timeout=self.original_guild.afk_timeout,
                                  verification_level=self.original_guild.verification_level,
                                  explicit_content_filter=self.original_guild.explicit_content_filter,
                                  splash=self.original_guild.splash,
                                  default_notifications=self.original_guild.default_notifications,
                                  system_channel=system_channel,
                                  system_channel_flags=self.original_guild.system_channel_flags,
                                  preferred_locale=self.original_guild.preferred_locale,
                                  premium_progress_bar_enabled=self.original_guild.premium_progress_bar_enabled,
                                  )
        print(f'> ⚙️ | Guild Settings Edited')

    async def disable_community(self):
        await self.new_guild.edit(community=False)
        print(f'> ⚙️ | Community Disabled')

    async def enable_community(self):
        if self.original_guild.rules_channel is not None and self.original_guild.public_updates_channel is not None:
            self.is_community = True
            rules_channel = None
            public_updates_channel = None
            safety_alerts_channel = None
            if self.original_guild.rules_channel is not None:
                rules_channel = self.mirror_channels[self.original_guild.rules_channel]
            if self.original_guild.public_updates_channel is not None:
                public_updates_channel = self.mirror_channels[self.original_guild.public_updates_channel]
            await self.new_guild.edit(community=True,
                                      rules_channel=rules_channel,
                                      public_updates_channel=public_updates_channel)
            print(f'> ⚙️ | Community Enabled')

    async def clean_roles(self):
        print('> 🧹 | Cleaning roles')
        for role in self.new_guild.roles:
            if not role.is_default() and not role.is_bot_managed() and not role.is_premium_subscriber() and not role.is_integration():
                await role.delete()
                print(f'- ❌ | Role deleted: {role.name}')
            await asyncio.sleep(self.copy_interval)

    async def clone_roles(self):
        print(f'> 🧬 | Cloning roles')
        for role in self.original_guild.roles[::-1]:
            if not role.is_default() and not role.is_bot_managed() and not role.is_premium_subscriber() and not role.is_integration():
                cloned_role = await self.new_guild.create_role(name=role.name, permissions=role.permissions,
                                                               color=role.color, mentionable=role.mentionable,
                                                               hoist=role.hoist)
                self.mirror_roles[role] = cloned_role
                print(f'- ➕ | Role cloned: {cloned_role.name}')
            elif role.is_default():
                await self.new_guild.default_role.edit(permissions=role.permissions)
                print(f'- ➕ | Changed Permissions for Default Role')
            elif role.is_premium_subscriber():
                for new_guild_role in self.new_guild.roles:
                    if new_guild_role.is_premium_subscriber():
                        await new_guild_role.edit(permissions=role.permissions)
                        print(f'- ➕ | Changed Permissions for Premium Subscriber Role')

            await asyncio.sleep(self.copy_interval)

    async def clean_channels(self):
        print('> 🧹 | Cleaning channels')
        for channel in self.new_guild.channels:
            await channel.delete()
            print(f'- ❌ | Channel deleted: {channel.name}')
            await asyncio.sleep(self.copy_interval)

    async def clone_categories(self):
        print(f'> 🧬 | Cloning categories')
        for category in self.original_guild.categories:
            cloned_category = await self.clone_category(category)
            self.mirror_channels[category] = cloned_category
            await asyncio.sleep(self.copy_interval)

    async def clone_text_channels(self):
        print(f'> 🧬 | Cloning text channels')
        for channel in self.original_guild.text_channels:
            cloned_channel = await self.clone_text_channel(channel)
            self.mirror_channels[channel] = cloned_channel
            await asyncio.sleep(self.copy_interval)

    async def clone_voice_channels(self):
        print(f'> 🧬 | Cloning voice channels')
        for channel in self.original_guild.voice_channels:
            cloned_channel = await self.clone_voice_channel(channel)
            self.mirror_channels[channel] = cloned_channel
            await asyncio.sleep(self.copy_interval)

    async def clone_forum_channels(self):
        print(f'> 🧬 | Cloning forum channels')
        for channel in self.original_guild.forums:
            cloned_channel = await self.clone_forum_channel(channel)
            self.mirror_channels[channel] = cloned_channel
            await asyncio.sleep(self.copy_interval)

    async def clone_stage_channels(self):
        print(f'> 🧬 | Cloning stage channels')
        for channel in self.original_guild.stage_channels:
            cloned_channel = await self.clone_stage_channel(channel)
            self.mirror_channels[channel] = cloned_channel
            await asyncio.sleep(self.copy_interval)

    async def clone_category(self, category):
        cloned_category = await self.new_guild.create_category(name=category.name, overwrites=category.overwrites)
        await self.__set_overwrites_for_channel(category, cloned_category)
        print(f'- ➕ | Category cloned: {cloned_category.name}')
        return cloned_category

    async def clone_text_channel(self, channel):
        category = self.__get_channel_category(channel)
        cloned_channel = await self.new_guild.create_text_channel(channel.name, category=category,
                                                                   position=channel.position,
                                                                   news=channel.is_news(),
                                                                   nsfw=channel.is_nsfw(), topic=channel.topic,
                                                                   slowmode_delay=channel.slowmode_delay,
                                                                   default_auto_archive_duration=channel.default_auto_archive_duration,
                                                                   default_thread_slowmode_delay=channel.default_thread_slowmode_delay)
        await self.__set_overwrites_for_channel(channel, cloned_channel)
        print(f'- ➕ | Text Channel cloned: {cloned_channel.name}')
        return cloned_channel

    async def clone_voice_channel(self, channel):
        category = self.__get_channel_category(channel)
        cloned_channel = await self.new_guild.create_voice_channel(channel.name, category=category,
                                                                   position=channel.position,
                                                                   bitrate=channel.bitrate,
                                                                   user_limit=channel.user_limit, rtc_region=channel.rtc_region,
                                                                   video_quality_mode=channel.video_quality_mode)
        await self.__set_overwrites_for_channel(channel, cloned_channel)
        print(f'- ➕ | Voice Channel cloned: {cloned_channel.name}')
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
                                                                   nsfw=channel.is_nsfw(),
                                                                   **additional_kwargs)
        await self.__set_overwrites_for_channel(channel, cloned_channel)
        print(f'- ➕ | Forum Channel cloned: {cloned_channel.name}')
        return cloned_channel

    async def clone_stage_channel(self, channel):
        category = self.__get_channel_category(channel)
        cloned_channel = await self.new_guild.create_stage_channel(channel.name, category=category,
                                                                   position=channel.position,
                                                                   bitrate=channel.bitrate,
                                                                   user_limit=channel.user_limit, rtc_region=channel.rtc_region,
                                                                   video_quality_mode=channel.video_quality_mode)
        await self.__set_overwrites_for_channel(channel, cloned_channel)
        print(f'- ➕ | Stage Channel cloned: {cloned_channel.name}')
        return cloned_channel

    async def clean_emojis(self):
        print(f'> 🧹 | Cleaning Emojis')
        for emoji in self.new_guild.emojis:
            await emoji.delete()
            print(f'- ❌ | Emoji deleted: {emoji.name}')
            await asyncio.sleep(self.copy_interval * 4)

    async def clone_emojis(self):
        print(f'> 🧬 | Cloning Emojis')
        for i, emoji in enumerate(self.original_guild.emojis):
            if i < self.original_guild.emoji_limit:
                for _ in range(3):
                    try:
                        emoji_image = await emoji.read()
                        cloned_emoji = await self.new_guild.create_custom_emoji(name=emoji.name, image=emoji_image)
                        print(f'- ➕ | Emoji cloned: {cloned_emoji.name}')
                        break
                    except Exception as e:
                        continue
            else:
                return
            await asyncio.sleep(self.copy_interval * 4)

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
                new_guild_role = self.mirror_roles[role]
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
